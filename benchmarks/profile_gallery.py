"""Frame-time breakdown for gallery.py in shader-only mode (hidden window).

Splits a frame into:
  build   imgui.new_frame -> imgui.render (Python UI + effect building)
  render  renderer.render CPU time (PyOpenGL dispatch)
  gpu     glFinish wait after render (GPU fill / program switches)
  swap    swap_buffers

Run: uv run python benchmarks/profile_gallery.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "example" / "anim"))

import glfw
import OpenGL.GL as gl

from slimgui import anim, imgui

glfw.init()
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
window = glfw.create_window(1900, 960, "gallery profile", None, None)
glfw.make_context_current(window)
glfw.swap_interval(0)

imgui.create_context()

import gallery
import showcase
from gallery import _create_checker_texture, draw_gallery
from fragfx_renderer import VfxShaderGlfwRenderer

gallery._SHOW_NATIVE = False  # shader-only mode

renderer = VfxShaderGlfwRenderer(window)
renderer.renderer.warmup(showcase.showcase_templates())
texture_id = _create_checker_texture()
showcase.set_demo_texture(texture_id)

N_WARM, N = 30, 200
t_build = t_render = t_gpu = t_swap = 0.0
n_cmds = n_effects = 0

for frame in range(N_WARM + N):
    measured = frame >= N_WARM
    glfw.poll_events()
    gl.glClearColor(0.045, 0.048, 0.060, 1.0)
    gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))

    t0 = time.perf_counter()
    renderer.new_frame()
    imgui.new_frame()
    anim.update_begin_frame()
    imgui.set_next_window_size((1840, 900), imgui.Cond.FIRST_USE_EVER)
    imgui.begin("VFX Gallery")
    draw_gallery(texture_id)
    imgui.end()
    imgui.render()
    t1 = time.perf_counter()

    draw_data = imgui.get_draw_data()
    if measured and frame == N_WARM:  # count once
        import fragfx
        for dl in draw_data.commands_lists:
            for cmd in dl.commands:
                n_cmds += 1
                if isinstance(cmd.callback_userdata, fragfx.Effect):
                    n_effects += 1

    renderer.render(draw_data)
    t2 = time.perf_counter()
    gl.glFinish()
    t3 = time.perf_counter()
    glfw.swap_buffers(window)
    t4 = time.perf_counter()

    if measured:
        t_build += t1 - t0
        t_render += t2 - t1
        t_gpu += t3 - t2
        t_swap += t4 - t3

ms = lambda t: t / N * 1e3
total = ms(t_build + t_render + t_gpu + t_swap)
print(f"draw commands/frame: {n_cmds} (effects: {n_effects})")
print(f"build  (python ui + effects): {ms(t_build):6.2f} ms")
print(f"render (pyopengl dispatch):   {ms(t_render):6.2f} ms")
print(f"gpu    (glFinish wait):       {ms(t_gpu):6.2f} ms")
print(f"swap:                         {ms(t_swap):6.2f} ms")
print(f"total: {total:.2f} ms  (~{1000.0 / total:.0f} fps)")

renderer.shutdown()
imgui.destroy_context(None)
glfw.terminate()
