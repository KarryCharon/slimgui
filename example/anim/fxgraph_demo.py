"""
Custom composed effects demo for `fragfx`.

Every helper in `fragfx` is a preset built from the expression
vocabulary in `fragfx.expr`. This demo builds effects the old
primitive+mode system could not express without new shader modes, purely by
composing the same building blocks in Python:

1. rainbow_glint: glint band profile x HSV coloring along the perimeter.
2. aurora_glow:   outer glow whose hue cycles around the border.
3. masked_glass:  material pad gated by a sweeping band mask.

The window also shows the compiled-program count: it stays constant while
everything animates, because animated values are uniforms and only the tree
*structure* keys the shader cache.

Run from this directory: python fxgraph_demo.py
"""

import math
import time

import OpenGL.GL as gl

from slimgui import imgui
from fragfx import Effect
from fragfx.math import clamp, fract, smooth01, pow
from fragfx.profiles import smoothfall, tent, wrap_delta, gauss
from fragfx.color import hsv2rgb, rgba
from fragfx.blocks import material_pad
from fragfx.effects import FRAG, RoundedRect

from fragfx_renderer import VfxShaderGlfwRenderer
from util import load_chinese_font, emit

Point = tuple[float, float]


# -- custom effects -------------------------------------------------------------


def rainbow_glint(
    p_min: Point,
    p_max: Point,
    rounding: float,
    progress: float,
    width: float = 6.0,
    length: float = 0.18,
    softness: float = 1.0,
    inset: float = 1.5,
    intensity: float = 0.9,
    hue_shift: float = 0.0,
) -> Effect:
    """Glint sweep colored by an HSV cycle along the border path."""
    rect = RoundedRect(p_min, p_max, rounding)
    band = tent((rect.sdf + inset) / max(width * 0.5, 0.5))
    delta = wrap_delta(rect.path_t, progress % 1.0)
    sweep = pow(1.0 - smooth01(0.0, 1.0, delta / (length * 0.5)), 1.0 / softness)
    color = hsv2rgb(fract(rect.path_t + hue_shift), 0.85, 1.0)
    pad = width * 0.5 + 2.0
    return Effect(rgba(color, band * sweep * intensity), (p_min[0] - pad, p_min[1] - pad), (p_max[0] + pad, p_max[1] + pad))


def aurora_glow(
    p_min: Point,
    p_max: Point,
    rounding: float,
    hue_shift: float,
    spread: float = 20.0,
    intensity: float = 0.6,
) -> Effect:
    """Outer glow whose hue cycles around the perimeter (glow x rainbow)."""
    rect = RoundedRect(p_min, p_max, rounding)
    t = clamp(rect.sdf / spread, 0.0, 1.0)
    alpha = smoothfall(t) * smooth01(-2.0, 0.0, rect.sdf) * intensity
    color = hsv2rgb(fract(rect.path_t + hue_shift), 0.7, 1.0)
    pad = spread + 2.0
    return Effect(rgba(color, alpha), (p_min[0] - pad, p_min[1] - pad), (p_max[0] + pad, p_max[1] + pad))


def masked_glass(
    p_min: Point,
    p_max: Point,
    rounding: float,
    progress: float,
    thickness: float = 12.0,
    intensity: float = 0.85,
) -> Effect:
    """Material pad revealed by a band sweeping left to right (material x mask)."""
    pad_color = material_pad(
        p_min,
        p_max,
        rounding,
        intensity,
        (1.0, 1.0, 1.0, 0.9),
        thickness,
        angle=-0.7853981633974483,
        metallic=0.0,
        roughness=0.25,
        specular=0.9,
        softness=0.4,
    )
    w = p_max[0] - p_min[0]
    band_center = p_min[0] + w * (progress % 1.0)
    mask = gauss((FRAG.x - band_center) / (w * 0.22))
    return Effect(rgba(pad_color.rgb, pad_color.a * mask), p_min, p_max)


# -- demo UI ----------------------------------------------------------------------

_BOX_W = 300.0
_BOX_H = 80.0
_ROUNDING = 16.0
_START_TIME = time.monotonic()


def _col(r: float, g: float, b: float, a: float) -> int:
    return imgui.color_convert_float4_to_u32((r, g, b, a))


def _effect_box(title: str, note: str, draw_fn) -> None:
    imgui.text(title)
    imgui.text_disabled(note)
    pos = imgui.get_cursor_screen_pos()
    p_min = (pos[0], pos[1])
    p_max = (pos[0] + _BOX_W, pos[1] + _BOX_H)
    draw_list = imgui.get_window_draw_list()
    draw_list.add_rect_filled(p_min, p_max, _col(0.13, 0.14, 0.18, 1.0), _ROUNDING)
    draw_fn(draw_list, p_min, p_max)
    imgui.dummy((_BOX_W, _BOX_H))
    imgui.dummy((1.0, 8.0))


def draw_demo(renderer) -> None:
    t = time.monotonic() - _START_TIME

    _effect_box(
        "rainbow_glint",
        "glint 剖面 x HSV 周长着色",
        lambda dl, a, b: emit(dl, rainbow_glint(a, b, _ROUNDING, t / 3.0, hue_shift=t / 6.0)),
    )
    _effect_box(
        "aurora_glow",
        "外发光 x HSV 周长着色",
        lambda dl, a, b: emit(dl, aurora_glow(a, b, _ROUNDING, t / 5.0, spread=16.0 + 6.0 * math.sin(t * 1.7))),
    )
    _effect_box(
        "masked_glass",
        "material pad x 扫动遮罩",
        lambda dl, a, b: emit(dl, masked_glass(a, b, _ROUNDING, t / 2.8)),
    )

    imgui.separator()
    imgui.text_disabled(f"compiled effect programs: {renderer.effect_compile_count} (动画中应保持稳定: 数值都是 uniform, 树形状才是缓存 key)")


def main():
    import glfw

    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(420, 540, "fragfx_renderer: custom composed effects", None, None)
    glfw.make_context_current(window)
    glfw.swap_interval(1)

    imgui.create_context()
    load_chinese_font()
    renderer = VfxShaderGlfwRenderer(window)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        gl.glClearColor(0.045, 0.048, 0.060, 1.0)
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))

        renderer.new_frame()
        imgui.new_frame()

        imgui.set_next_window_size((390, 500), imgui.Cond.FIRST_USE_EVER)
        imgui.set_next_window_pos((15, 15), imgui.Cond.FIRST_USE_EVER)
        imgui.begin("composed effects")
        draw_demo(renderer.renderer)
        imgui.end()

        imgui.render()
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    renderer.shutdown()
    imgui.destroy_context(None)


if __name__ == "__main__":
    main()
