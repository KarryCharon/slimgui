import glfw
import OpenGL.GL as gl

from fragfx import effects as fxe
from slimgui import anim, imgui
from util import emit
from fragfx_renderer import VfxShaderGlfwRenderer

SCAN_SECONDS = 1.8


def _col(r: float, g: float, b: float, a: float) -> int:
    return imgui.color_convert_float4_to_u32((r, g, b, a))


def _anim_id(item_id: int, channel: str) -> int:
    return item_id ^ anim.hash_str(channel)


def shimmer_button(label: str, size: tuple[float, float]) -> bool:
    draw_list = imgui.get_window_draw_list()
    pos = imgui.get_cursor_screen_pos()
    clicked = imgui.invisible_button(f"##{label}", size)

    item_id = anim.hash_str(label)
    io = imgui.get_io()

    x, y = pos
    w, h = size
    rounding = 20.0

    scan_progress = (
        anim.oscillate(
            _anim_id(item_id, "scan"),
            1.0,
            1.0 / SCAN_SECONDS,
            anim.WAVE_SAWTOOTH,
            0.0,
            io.delta_time,
        )
        + 1.0
    ) * 0.5

    draw_list.add_rect_filled((x, y), (x + w, y + h), _col(0.16, 0.42, 0.86, 1.0), rounding)

    emit(draw_list, fxe.shimmer_band(
        (x, y),
        (x + w, y + h),
        rounding=rounding,
        progress=scan_progress,
        width=0.40,
        intensity=0.38,
    ))

    draw_list.add_rect((x, y), (x + w, y + h), _col(1.0, 1.0, 1.0, 0.45), rounding, thickness=1.5)

    text_size = imgui.calc_text_size(label)
    text_pos = (x + (w - text_size[0]) * 0.5, y + (h - text_size[1]) * 0.5)
    draw_list.add_text((text_pos[0] + 1.0, text_pos[1] + 1.0), _col(0.0, 0.0, 0.0, 0.35), label)
    draw_list.add_text(text_pos, imgui.COL32_WHITE, label)
    return clicked


def main():
    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(520, 260, "slimgui shimmer button", None, None)
    glfw.make_context_current(window)
    glfw.swap_interval(0)

    imgui.create_context()
    renderer = VfxShaderGlfwRenderer(window)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))

        renderer.new_frame()
        imgui.new_frame()
        anim.update_begin_frame()

        imgui.set_next_window_size((460, 200), imgui.Cond.FIRST_USE_EVER)
        imgui.begin("Shimmer button")
        shimmer_button("Generate", (360, 96))
        imgui.end()

        imgui.render()
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    renderer.shutdown()
    imgui.destroy_context(None)


if __name__ == "__main__":
    main()
