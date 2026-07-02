"""
Experimental OpenGL backend for `fragfx` effects emitted through slimgui.

`VfxShaderOpenGLRenderer` extends the stock `OpenGLRenderer` with effect
dispatch: emitted effects travel through the command stream as callback
userdata, and the renderer recognizes `fragfx.Effect` payloads in its own
draw data (`cmd.callback_userdata`) and draws them itself -- no device
registry, no callback execution. Multi-context isolation is automatic:
each renderer only ever sees the draw data of the context it renders.

There are no hand-written effect shaders: the renderer generates GLSL from
the expression graph on first use (via the built-in `fragfx.glsl` dialect)
and caches the compiled program by the graph's *structure*. Animated
parameters are uniforms (packed into one `UParams[]` array), so animation
never recompiles.

Each draw is self-contained: bind own program/VAO, draw a coverage quad,
restore the default imgui program/VAO before returning.
"""

import ctypes

import OpenGL.GL as gl

import fragfx
from slimgui import imgui
from slimgui.integrations.glfw import GlfwRenderer
from slimgui.integrations.opengl import OpenGLRenderer

_VERTEX_SHADER_SRC = """
#version 330

uniform mat4 ProjMtx;
layout(location = 0) in vec2 Position;
out vec2 Frag_Pos;

void main() {
    Frag_Pos = Position;
    gl_Position = ProjMtx * vec4(Position.xy, 0, 1);
}
"""

_QUAD_POSITION_LOCATION = 0


class VfxShaderOpenGLRenderer(OpenGLRenderer):
    def __init__(self):
        super().__init__()
        self._fb_height: int = 0
        # structure key -> (program, ProjMtx loc, UParams loc, n_params)
        self._effect_programs: dict[tuple, tuple[int, int, int, int]] = {}
        self.effect_compile_count: int = 0
        # ProjMtx is program state: upload once per program per display size
        # instead of rebuilding/uploading the matrix on every effect draw.
        self._display_size: tuple[float, float] = (0.0, 0.0)
        self._proj_mtx = (ctypes.c_float * 16)()
        self._proj_uploaded: dict[int, tuple[float, float]] = {}
        self._create_quad_objects(_QUAD_POSITION_LOCATION)

    # -- GL object setup -------------------------------------------------

    def _compile_program(self, vertex_src: str, fragment_src: str) -> int:
        program = gl.glCreateProgram()
        for src, kind in ((vertex_src, gl.GL_VERTEX_SHADER), (fragment_src, gl.GL_FRAGMENT_SHADER)):
            shader = gl.glCreateShader(kind)
            gl.glShaderSource(shader, src)
            gl.glCompileShader(shader)
            if not gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS):
                raise RuntimeError(gl.glGetShaderInfoLog(shader).decode())
            gl.glAttachShader(program, shader)
            gl.glDeleteShader(shader)
        gl.glLinkProgram(program)
        if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
            raise RuntimeError(gl.glGetProgramInfoLog(program).decode())
        return program

    def _create_quad_objects(self, position_location: int) -> None:
        last_array_buffer = gl.glGetIntegerv(gl.GL_ARRAY_BUFFER_BINDING)
        last_vertex_array = gl.glGetIntegerv(gl.GL_VERTEX_ARRAY_BINDING)

        self._quad_vao: int = gl.glGenVertexArrays(1)
        self._quad_vbo: int = gl.glGenBuffers(1)
        gl.glBindVertexArray(self._quad_vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._quad_vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, 12 * 4, None, gl.GL_STREAM_DRAW)
        gl.glEnableVertexAttribArray(position_location)
        gl.glVertexAttribPointer(position_location, 2, gl.GL_FLOAT, gl.GL_FALSE, 0, ctypes.c_void_p(0))

        gl.glBindVertexArray(last_vertex_array)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, last_array_buffer)

    # -- render loop -----------------------------------------------------

    def render(self, draw_data: imgui.DrawData):
        # draw_effect runs inside the base loop and needs fb height to
        # convert clip rects to scissor coords.
        io = imgui.get_io()
        fb_scale = draw_data.framebuffer_scale
        self._fb_height = int(io.display_size[1] * fb_scale[1])
        display_size = (float(io.display_size[0]), float(io.display_size[1]))
        if display_size != self._display_size:
            display_width, display_height = display_size
            self._proj_mtx[:] = (
                 2.0/display_width, 0.0,                   0.0, 0.0,
                 0.0,               2.0/-display_height,   0.0, 0.0,
                 0.0,               0.0,                  -1.0, 0.0,
                -1.0,               1.0,                   0.0, 1.0,
            )  # fmt: skip
            self._display_size = display_size
            self._proj_uploaded.clear()
        super().render(draw_data)

    # -- effect dispatch ---------------------------------------------------

    def _run_cmd_callback(self, cmd: imgui.DrawCmd, drawlist: imgui.DrawList) -> imgui.DrawListCallbackResult:
        """Recognize emitted effects in the command stream and draw them
        directly instead of running their (fail-fast) callback."""
        fx = cmd.callback_userdata
        if isinstance(fx, fragfx.Effect):
            self.draw_effect(cmd, fx)
            return imgui.DrawListCallbackResult.CALLBACK
        return super()._run_cmd_callback(cmd, drawlist)

    def _ensure_program(self, key: tuple, color: fragfx.Expr) -> tuple[int, int, int, int]:
        entry = self._effect_programs.get(key)
        if entry is None:
            order, index = fragfx.linearize(color)
            gen = fragfx.generate(order, index)
            program = self._compile_program(_VERTEX_SHADER_SRC, fragfx.glsl.assemble_gl330(gen))
            if gen.uses_texture:
                # sampler binding is program state: set it once
                gl.glUseProgram(program)
                gl.glUniform1i(gl.glGetUniformLocation(program, "Texture"), 0)
            entry = (
                program,
                gl.glGetUniformLocation(program, "ProjMtx"),
                gl.glGetUniformLocation(program, "UParams"),
                gen.n_params,
            )
            self._effect_programs[key] = entry
            self.effect_compile_count += 1
        return entry

    def warmup(self, templates: "list[fragfx.Template] | None" = None) -> None:
        """Pre-compile effect programs (e.g. all helper presets) so first
        use causes no compile hitch. Call with a current GL context."""
        if templates is None:
            templates = fragfx.preset_templates()
        for template in templates:
            self._ensure_program(template.key, template.color)

    def draw_effect(self, cmd: imgui.DrawCmd, fx: fragfx.Effect) -> None:
        key, values = fx.key, fx.values
        if key is None or values is None:
            order, index = fragfx.linearize(fx.color)
            if key is None:
                key = fragfx.structure_key(order, index)
            if values is None:
                values = fragfx.collect_params(order)
        program, proj_loc, params_loc, n_params = self._ensure_program(key, fx.color)

        gl.glUseProgram(program)
        if self._proj_uploaded.get(program) != self._display_size:
            gl.glUniformMatrix4fv(proj_loc, 1, gl.GL_FALSE, self._proj_mtx)
            self._proj_uploaded[program] = self._display_size
        if n_params:
            gl.glUniform1fv(params_loc, n_params, (ctypes.c_float * n_params)(*values))
        if fx.texture_id is not None:
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, fx.texture_id)

        # scissor from the active clip rect (already in fb coords)
        x, y, z, w = cmd.clip_rect
        gl.glScissor(int(x), int(self._fb_height - w), int(z - x), int(w - y))

        (x0, y0), (x1, y1) = fx.p_min, fx.p_max
        quad = (ctypes.c_float * 12)(x0, y0, x1, y0, x1, y1, x0, y0, x1, y1, x0, y1)
        gl.glBindVertexArray(self._quad_vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._quad_vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(quad), quad, gl.GL_STREAM_DRAW)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)

        # The imgui VAO carries the element buffer binding and attrib
        # pointers; textures and scissor are re-set per draw command.
        gl.glBindVertexArray(self._vao_handle)
        gl.glUseProgram(self._shader_handle)

    # -- shutdown --------------------------------------------------------

    def shutdown(self):
        for program, *_locs in self._effect_programs.values():
            gl.glDeleteProgram(program)
        self._effect_programs.clear()
        self._proj_uploaded.clear()
        if self._quad_vao:
            gl.glDeleteVertexArrays(1, [self._quad_vao])
            self._quad_vao = 0
        if self._quad_vbo:
            gl.glDeleteBuffers(1, [self._quad_vbo])
            self._quad_vbo = 0
        super().shutdown()


class VfxShaderGlfwRenderer(GlfwRenderer):
    def __init__(self, window, warmup: bool = True, **kwargs):
        super().__init__(window, **kwargs)
        self.renderer.shutdown()
        self.renderer = VfxShaderOpenGLRenderer()
        plat_io = imgui.get_platform_io()
        plat_io.renderer_texture_max_height = self.renderer.max_texture_size
        plat_io.renderer_texture_max_width = self.renderer.max_texture_size
        if warmup:
            self.renderer.warmup()
