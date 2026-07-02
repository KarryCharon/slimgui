import math

import showcase

from util import load_chinese_font, emit
from fragfx import effects as fxe
from slimgui import anim, imgui

_RIPPLE_CENTERS: dict[int, tuple[float, float]] = {}
_RIPPLE_START_TIMES: dict[int, float] = {}
_WATER_CENTERS: dict[int, tuple[float, float]] = {}
_WATER_START_TIMES: dict[int, float] = {}
_WATER_SEEDS: dict[int, float] = {}
_FLASH_CENTERS: dict[int, tuple[float, float]] = {}
_FLASH_START_TIMES: dict[int, float] = {}
_SHOCKWAVE_CENTERS: dict[int, tuple[float, float]] = {}
_SHOCKWAVE_START_TIMES: dict[int, float] = {}
_SPARK_CENTERS: dict[int, tuple[float, float]] = {}
_SPARK_START_TIMES: dict[int, float] = {}
_GALLERY_CARD_WIDTH = 336.0
_GALLERY_CARD_HEIGHT = 112.0
_GALLERY_CARD_GAP = 8.0
_GALLERY_CARD_ROW_HEIGHT = _GALLERY_CARD_HEIGHT + _GALLERY_CARD_GAP
_GALLERY_PREVIEW_PAD_X = 10.0
_GALLERY_PREVIEW_PAD_Y = 36.0
_GALLERY_PREVIEW_WIDTH = _GALLERY_CARD_WIDTH - _GALLERY_PREVIEW_PAD_X * 2.0
_GALLERY_PREVIEW_HEIGHT = 68.0


def _col(r: float, g: float, b: float, a: float) -> int:
    return imgui.color_convert_float4_to_u32((r, g, b, a))


def _anim_id(item_id: int, channel: str) -> int:
    return item_id ^ anim.hash_str(channel)


def _cycle(item_id: int, channel: str, seconds: float, phase: float = 0.0) -> float:
    io = imgui.get_io()
    return (
        anim.oscillate(
            _anim_id(item_id, channel),
            1.0,
            1.0 / seconds,
            anim.WAVE_SAWTOOTH,
            phase,
            io.delta_time,
        )
        + 1.0
    ) * 0.5


def _rounded_rect_point_at(
    p_min: tuple[float, float],
    p_max: tuple[float, float],
    rounding: float,
    progress: float,
) -> tuple[float, float]:
    x0, y0 = p_min
    x1, y1 = p_max
    w = x1 - x0
    h = y1 - y0
    r = max(0.0, min(rounding, min(w, h) * 0.5))
    top_len = max(w - r * 2.0, 0.0)
    side_len = max(h - r * 2.0, 0.0)
    arc_len = math.pi * r * 0.5
    perimeter = top_len * 2.0 + side_len * 2.0 + arc_len * 4.0
    if perimeter <= 0.0:
        return ((x0 + x1) * 0.5, (y0 + y1) * 0.5)

    s = (progress % 1.0) * perimeter
    if s < top_len:
        return (x0 + r + s, y0)
    s -= top_len

    if s < arc_len:
        a = -math.pi * 0.5 + (s / arc_len if arc_len > 0.0 else 0.0) * math.pi * 0.5
        return (x1 - r + math.cos(a) * r, y0 + r + math.sin(a) * r)
    s -= arc_len

    if s < side_len:
        return (x1, y0 + r + s)
    s -= side_len

    if s < arc_len:
        a = (s / arc_len if arc_len > 0.0 else 0.0) * math.pi * 0.5
        return (x1 - r + math.cos(a) * r, y1 - r + math.sin(a) * r)
    s -= arc_len

    if s < top_len:
        return (x1 - r - s, y1)
    s -= top_len

    if s < arc_len:
        a = math.pi * 0.5 + (s / arc_len if arc_len > 0.0 else 0.0) * math.pi * 0.5
        return (x0 + r + math.cos(a) * r, y1 - r + math.sin(a) * r)
    s -= arc_len

    if s < side_len:
        return (x0, y1 - r - s)
    s -= side_len

    a = math.pi + (s / arc_len if arc_len > 0.0 else 0.0) * math.pi * 0.5
    return (x0 + r + math.cos(a) * r, y0 + r + math.sin(a) * r)


def _create_checker_texture(size: int = 96) -> int:
    import OpenGL.GL as gl

    pixels = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            tile = ((x // 12) + (y // 12)) % 2
            tint = 210 if tile else 92
            offset = (y * size + x) * 4
            pixels[offset : offset + 4] = (tint, 120 + tile * 80, 255 - tile * 50, 255)

    tex_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, size, size, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, bytes(pixels))
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
    return tex_id


def _draw_shader_shimmer_band(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 18.0
    progress = _cycle(item_id, "shader_shimmer_band", 1.8)

    draw_list.add_rect_filled(
        (x, y),
        (x + w, y + h),
        _col(0.13, 0.32, 0.72, 1.0),
        rounding,
    )
    emit(
        draw_list,
        fxe.shimmer_band(
            (x, y),
            (x + w, y + h),
            rounding=rounding,
            progress=progress,
            width=0.34,
            intensity=0.52,
        ),
    )
    draw_list.add_rect(
        (x, y),
        (x + w, y + h),
        _col(1.0, 1.0, 1.0, 0.35),
        rounding,
        thickness=1.3,
    )


def _draw_shader_radial_gleam(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 22.0
    phase = _cycle(item_id, "shader_radial_gleam", 2.6)
    p_min = (x, y)
    p_max = (x + w, y + h)
    center = (
        x + w * (0.5 + math.cos(phase * math.tau) * 0.34),
        y + h * (0.5 + math.sin(phase * math.tau) * 0.26),
    )

    draw_list.add_rect_filled(p_min, p_max, _col(0.07, 0.11, 0.18, 1.0), rounding)
    emit(
        draw_list,
        fxe.radial_gleam(
            p_min,
            p_max,
            center,
            rounding=rounding,
            radius=118.0,
            intensity=0.58,
            color=(0.82, 0.95, 1.0, 1.0),
            aspect=0.58,
        ),
    )
    draw_list.add_rect(p_min, p_max, _col(0.62, 0.82, 1.0, 0.28), rounding, thickness=1.2)


def _draw_shader_glass_pad(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 22.0
    # the light azimuth is adjustable: orbit it slowly to show it off
    phase = _cycle(item_id, "shader_glass_pad", 6.0)
    angle = phase * math.tau

    emit(
        draw_list,
        fxe.glass_pad(
            (x, y),
            (x + w, y + h),
            rounding=rounding,
            thickness=13.0,
            intensity=0.8,
            color=(0.24, 0.52, 0.22, 1.0),
            angle=angle,
        ),
    )


def _draw_shader_metal_pad(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 22.0
    phase = _cycle(item_id, "shader_metal_pad", 6.0)
    angle = phase * math.tau

    emit(
        draw_list,
        fxe.metal_pad(
            (x, y),
            (x + w, y + h),
            rounding=rounding,
            thickness=13.0,
            intensity=0.8,
            color=(0.78, 0.62, 0.22, 1.0),
            angle=angle,
            roughness=0.35,
        ),
    )


def _draw_shader_rounded_rect_glint(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    progress = _cycle(item_id, "shader_rounded_rect_glint", 2.4)

    draw_list.add_rect_filled((x, y), (x + w, y + h), _col(0.10, 0.11, 0.16, 1.0), rounding)
    draw_list.add_rect_filled((x + 18.0, y + 18.0), (x + w - 18.0, y + h - 18.0), _col(0.17, 0.18, 0.26, 1.0), 16.0)
    emit(
        draw_list,
        fxe.rounded_rect_glint(
            (x + 8.0, y + 8.0),
            (x + w - 8.0, y + h - 8.0),
            rounding=rounding,
            progress=progress,
            width=8.0,
            length=0.26,
            color=(1.0, 0.82, 0.32, 0.95),
            softness=1.15,
            inset=0.0,
            corner_colors=(
                (0.30, 0.92, 1.0, 1.0),
                (1.0, 0.86, 0.30, 1.0),
                (1.0, 0.36, 0.75, 1.0),
                (0.45, 1.0, 0.50, 1.0),
            ),
        ),
    )


def _draw_shader_corner_glints(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 28.0
    progress = _cycle(item_id, "shader_corner_glints", 1.7)
    p_min = (x + 10.0, y + 8.0)
    p_max = (x + w - 10.0, y + h - 8.0)

    draw_list.add_rect_filled(p_min, p_max, _col(0.08, 0.09, 0.14, 1.0), rounding)
    draw_list.add_rect(p_min, p_max, _col(0.48, 0.58, 0.75, 0.26), rounding, thickness=1.2)
    emit(
        draw_list,
        fxe.corner_glints(
            p_min,
            p_max,
            rounding=rounding,
            progress=progress,
            width=8.0,
            length=0.62,
            intensity=0.92,
            color=(1.0, 0.86, 0.34, 1.0),
            softness=1.2,
            inset=3.0,
        ),
    )


def _draw_shader_soft_glow_rect(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    progress = _cycle(item_id, "shader_soft_glow_rect", 2.2)
    pulse = 1.0 - abs(progress * 2.0 - 1.0)

    emit(
        draw_list,
        fxe.soft_glow_rect(
            (x + 18.0, y + 14.0),
            (x + w - 18.0, y + h - 14.0),
            rounding=rounding,
            spread=24.0 + pulse * 10.0,
            intensity=0.34 + pulse * 0.18,
            color=(0.20, 0.62, 1.0, 1.0),
        ),
    )
    draw_list.add_rect_filled(
        (x + 18.0, y + 14.0),
        (x + w - 18.0, y + h - 14.0),
        _col(0.08, 0.12, 0.18, 1.0),
        rounding,
    )
    draw_list.add_rect(
        (x + 18.0, y + 14.0),
        (x + w - 18.0, y + h - 14.0),
        _col(0.58, 0.78, 1.0, 0.46),
        rounding,
        thickness=1.2,
    )


def _draw_shader_rounded_rect_border_glow(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 26.0
    progress = _cycle(item_id, "shader_rounded_rect_border_glow", 2.0)
    pulse = 1.0 - abs(progress * 2.0 - 1.0)
    p_min = (x + 18.0, y + 14.0)
    p_max = (x + w - 18.0, y + h - 14.0)

    draw_list.add_rect_filled(p_min, p_max, _col(0.08, 0.10, 0.15, 1.0), rounding)
    emit(
        draw_list,
        fxe.rounded_rect_border_glow(
            p_min,
            p_max,
            rounding=rounding,
            width=2.5 + pulse * 1.2,
            spread=12.0 + pulse * 8.0,
            intensity=0.48 + pulse * 0.25,
            color=(0.40, 0.82, 1.0, 1.0),
        ),
    )


def _draw_shader_neon_tube_border(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 26.0
    progress = _cycle(item_id, "shader_neon_tube_border", 1.6)
    flicker = 0.85 + 0.15 * math.sin(progress * math.tau * 3.0)
    p_min = (x + 18.0, y + 14.0)
    p_max = (x + w - 18.0, y + h - 14.0)

    draw_list.add_rect_filled(p_min, p_max, _col(0.05, 0.06, 0.10, 1.0), rounding)
    emit(
        draw_list,
        fxe.neon_tube_border(
            p_min,
            p_max,
            rounding=rounding,
            width=3.2,
            glow_width=20.0,
            intensity=0.78 * flicker,
            color=(0.22, 0.95, 1.0, 1.0),
            core_color=(0.92, 1.0, 1.0, 1.0),
        ),
    )


def _draw_shader_rainbow_border(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 26.0
    progress = _cycle(item_id, "shader_rainbow_border", 3.0)
    p_min = (x + 18.0, y + 14.0)
    p_max = (x + w - 18.0, y + h - 14.0)

    draw_list.add_rect_filled(p_min, p_max, _col(0.06, 0.07, 0.11, 1.0), rounding)
    emit(
        draw_list,
        fxe.rainbow_border(
            p_min,
            p_max,
            rounding=rounding,
            progress=progress,
            width=4.0,
            intensity=0.9,
        ),
    )


def _draw_shader_inner_glow_rect(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    progress = _cycle(item_id, "shader_inner_glow_rect", 2.2)
    pulse = 1.0 - abs(progress * 2.0 - 1.0)

    draw_list.add_rect_filled(
        (x + 18.0, y + 14.0),
        (x + w - 18.0, y + h - 14.0),
        _col(0.08, 0.12, 0.18, 1.0),
        rounding,
    )
    emit(
        draw_list,
        fxe.inner_glow_rect(
            (x + 18.0, y + 14.0),
            (x + w - 18.0, y + h - 14.0),
            rounding=rounding,
            spread=16.0 + pulse * 12.0,
            intensity=0.45 + pulse * 0.25,
            color=(0.30, 0.72, 1.0, 1.0),
        ),
    )
    draw_list.add_rect(
        (x + 18.0, y + 14.0),
        (x + w - 18.0, y + h - 14.0),
        _col(0.58, 0.78, 1.0, 0.46),
        rounding,
        thickness=1.2,
    )


def _draw_shader_click_ripple(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)

    clicked = imgui.invisible_button("##shader_click_ripple_demo", (w, h))
    if clicked:
        _RIPPLE_CENTERS[item_id] = imgui.get_mouse_pos()
        _RIPPLE_START_TIMES[item_id] = imgui.get_time()

    draw_list.add_rect_filled(p_min, p_max, _col(0.10, 0.12, 0.19, 1.0), rounding)

    if item_id in _RIPPLE_START_TIMES:
        progress = min((imgui.get_time() - _RIPPLE_START_TIMES[item_id]) / 0.95, 1.0)
        center = _RIPPLE_CENTERS[item_id]
    else:
        progress = _cycle(item_id, "shader_click_ripple_auto", 1.9)
        center = ((p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5)

    if progress < 1.0:
        emit(
            draw_list,
            fxe.click_ripple(
                p_min,
                p_max,
                center,
                rounding=rounding,
                progress=progress,
                radius=205.0,
                width=34.0,
                intensity=0.36,
                color=(0.58, 0.86, 1.0, 0.72),
            ),
        )

    draw_list.add_rect(p_min, p_max, _col(0.72, 0.88, 1.0, 0.34), rounding, thickness=1.2)


def _draw_shader_water_ripple(draw_list: imgui.DrawList, pos: tuple[float, float], texture_id: int, item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)

    clicked = imgui.invisible_button("##shader_water_ripple_demo", (w, h))
    if clicked:
        _WATER_CENTERS[item_id] = imgui.get_mouse_pos()
        _WATER_START_TIMES[item_id] = imgui.get_time()
        _WATER_SEEDS[item_id] = imgui.get_time() * 7.3 % 100.0

    if item_id in _WATER_START_TIMES:
        progress = min((imgui.get_time() - _WATER_START_TIMES[item_id]) / 1.6, 1.0)
        center = _WATER_CENTERS[item_id]
        seed = _WATER_SEEDS[item_id]
    else:
        progress = _cycle(item_id, "shader_water_ripple_auto", 2.6)
        center = ((p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5)
        seed = 3.1

    showcase.water_ripple_refract(
        draw_list,
        texture_id,
        p_min,
        p_max,
        center,
        progress,
        seed=seed,
        rounding=rounding,
        uv_max=(w / 96.0, h / 96.0),
    )

    draw_list.add_rect(p_min, p_max, _col(0.5, 0.8, 1.0, 0.3), rounding, thickness=1.2)


def _draw_shader_press_flash(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)

    clicked = imgui.invisible_button("##shader_press_flash_demo", (w, h))
    if clicked:
        _FLASH_CENTERS[item_id] = imgui.get_mouse_pos()
        _FLASH_START_TIMES[item_id] = imgui.get_time()

    draw_list.add_rect_filled(p_min, p_max, _col(0.12, 0.10, 0.16, 1.0), rounding)

    if item_id in _FLASH_START_TIMES:
        progress = min((imgui.get_time() - _FLASH_START_TIMES[item_id]) / 0.42, 1.0)
        center = _FLASH_CENTERS[item_id]
    else:
        progress = _cycle(item_id, "shader_press_flash_auto", 1.35)
        center = ((p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5)

    if progress < 1.0:
        emit(
            draw_list,
            fxe.press_flash(
                p_min,
                p_max,
                center,
                rounding=rounding,
                progress=progress,
                radius=190.0,
                intensity=0.60,
                color=(1.0, 0.78, 0.45, 1.0),
            ),
        )

    draw_list.add_rect(p_min, p_max, _col(1.0, 0.78, 0.45, 0.32), rounding, thickness=1.2)


def _draw_shader_shockwave(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)

    clicked = imgui.invisible_button("##shader_shockwave_demo", (w, h))
    if clicked:
        _SHOCKWAVE_CENTERS[item_id] = imgui.get_mouse_pos()
        _SHOCKWAVE_START_TIMES[item_id] = imgui.get_time()

    draw_list.add_rect_filled(p_min, p_max, _col(0.08, 0.09, 0.14, 1.0), rounding)

    if item_id in _SHOCKWAVE_START_TIMES:
        progress = min((imgui.get_time() - _SHOCKWAVE_START_TIMES[item_id]) / 0.58, 1.0)
        center = _SHOCKWAVE_CENTERS[item_id]
    else:
        progress = _cycle(item_id, "shader_shockwave_auto", 1.45)
        center = ((p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5)

    if progress < 1.0:
        emit(
            draw_list,
            fxe.shockwave(
                p_min,
                p_max,
                center,
                rounding=rounding,
                progress=progress,
                radius=220.0,
                width=18.0,
                intensity=0.82,
                color=(0.60, 0.96, 1.0, 1.0),
            ),
        )

    draw_list.add_rect(p_min, p_max, _col(0.60, 0.96, 1.0, 0.32), rounding, thickness=1.2)


def _draw_shader_magnetic_edge_glow(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)

    imgui.invisible_button("##shader_magnetic_edge_glow_demo", (w, h))
    hovered = imgui.is_item_hovered()

    if hovered:
        pointer = imgui.get_mouse_pos()
        intensity = 0.68
    else:
        phase = _cycle(item_id, "shader_magnetic_edge_glow_auto", 3.4)
        pointer = _rounded_rect_point_at(p_min, p_max, rounding, phase)
        intensity = 0.36

    draw_list.add_rect_filled(p_min, p_max, _col(0.09, 0.12, 0.15, 1.0), rounding)
    emit(
        draw_list,
        fxe.magnetic_edge_glow(
            p_min,
            p_max,
            pointer,
            rounding=rounding,
            width=20.0,
            reach=150.0,
            intensity=intensity,
            color=(0.38, 0.92, 1.0, 1.0),
        ),
    )
    draw_list.add_rect(p_min, p_max, _col(0.38, 0.92, 1.0, 0.26), rounding, thickness=1.2)


def _draw_shader_state_transition_glow(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)
    phase = _cycle(item_id, "shader_state_transition_glow", 1.8)
    progress = min(phase / 0.42, 1.0)

    draw_list.add_rect_filled(p_min, p_max, _col(0.10, 0.10, 0.15, 1.0), rounding)
    if progress < 1.0:
        emit(
            draw_list,
            fxe.state_transition_glow(
                p_min,
                p_max,
                rounding=rounding,
                progress=progress,
                width=24.0,
                intensity=0.62,
                color=(0.68, 0.95, 1.0, 1.0),
            ),
        )
    draw_list.add_rect(p_min, p_max, _col(0.68, 0.95, 1.0, 0.24), rounding, thickness=1.2)


def _draw_shader_path_particles(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)
    progress = _cycle(item_id, "shader_path_particles", 2.8)

    draw_list.add_rect_filled(p_min, p_max, _col(0.08, 0.10, 0.14, 1.0), rounding)
    draw_list.add_rect(p_min, p_max, _col(0.42, 0.66, 0.78, 0.24), rounding, thickness=1.1)
    emit(
        draw_list,
        fxe.path_particles(
            p_min,
            p_max,
            rounding=rounding,
            progress=progress,
            count=24,
            radius=4.2,
            intensity=0.78,
            trail=0.42,
            inset=3.5,
            color=(0.62, 0.96, 1.0, 1.0),
        ),
    )


def _draw_shader_spark_burst(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)

    clicked = imgui.invisible_button("##shader_spark_burst_demo", (w, h))
    if clicked:
        _SPARK_CENTERS[item_id] = imgui.get_mouse_pos()
        _SPARK_START_TIMES[item_id] = imgui.get_time()

    draw_list.add_rect_filled(p_min, p_max, _col(0.12, 0.09, 0.11, 1.0), rounding)
    draw_list.add_rect(p_min, p_max, _col(1.0, 0.72, 0.38, 0.28), rounding, thickness=1.2)

    if item_id in _SPARK_START_TIMES:
        progress = min((imgui.get_time() - _SPARK_START_TIMES[item_id]) / 0.82, 1.0)
        center = _SPARK_CENTERS[item_id]
    else:
        progress = _cycle(item_id, "shader_spark_burst_auto", 1.65)
        center = ((p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5)

    if progress < 1.0:
        emit(
            draw_list,
            fxe.spark_burst(
                center,
                progress=progress,
                count=34,
                radius=3.4,
                spread=min(w, h) * 0.82,
                intensity=0.96,
                color=(1.0, 0.76, 0.34, 1.0),
            ),
        )


def _draw_shader_trail_dots(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 24.0
    p_min = (x, y)
    p_max = (x + w, y + h)
    phase = _cycle(item_id, "shader_trail_dots", 2.0)
    left = (x + 38.0, y + h * 0.52)
    right = (x + w - 38.0, y + h * 0.52)
    path_len = right[0] - left[0]
    tail_len = 12.0 * 17.0
    progress = phase * (1.0 + tail_len / path_len)

    draw_list.add_rect_filled(p_min, p_max, _col(0.08, 0.10, 0.14, 1.0), rounding)
    draw_list.add_rect(p_min, p_max, _col(0.58, 0.82, 1.0, 0.24), rounding, thickness=1.2)
    emit(
        draw_list,
        fxe.trail_dots(
            left,
            right,
            progress=progress,
            count=18,
            radius=4.0,
            spacing=12.0,
            intensity=0.82,
            color=(0.62, 0.88, 1.0, 1.0),
        ),
    )


def _draw_shader_focus_ring(draw_list: imgui.DrawList, pos: tuple[float, float], item_id: int) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 22.0
    phase = _cycle(item_id, "shader_focus_ring", 2.4)
    progress = min(max((phase - 0.08) / 0.28, 0.0), 1.0)

    draw_list.add_rect_filled((x, y), (x + w, y + h), _col(0.09, 0.11, 0.17, 1.0), rounding)
    draw_list.add_rect(
        (x, y),
        (x + w, y + h),
        _col(0.42, 0.52, 0.70, 0.45),
        rounding,
        thickness=1.0,
    )
    emit(
        draw_list,
        fxe.focus_ring(
            (x, y),
            (x + w, y + h),
            rounding=rounding,
            progress=progress,
            width=5.0,
            inset=-3.0,
            color=(0.45, 0.78, 1.0, 1.0),
        ),
    )


def _draw_shader_rounded_image_edge_fade(
    draw_list: imgui.DrawList,
    pos: tuple[float, float],
    texture_id: int,
    item_id: int,
) -> None:
    x, y = pos
    w, h = _GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT
    rounding = 28.0
    image_min = (x + 10.0, y + 8.0)
    image_max = (x + w - 10.0, y + h - 8.0)
    uv_scroll = _cycle(item_id, "shader_rounded_image_edge_fade", 4.0)

    draw_list.add_rect_filled((x, y), (x + w, y + h), _col(0.08, 0.10, 0.12, 1.0), rounding)
    draw_list.add_rect_filled(image_min, image_max, _col(0.02, 0.03, 0.04, 1.0), 18.0)
    emit(
        draw_list,
        fxe.rounded_image_edge_fade(
            texture_id,
            image_min,
            image_max,
            (uv_scroll, 0.0),
            (uv_scroll + 2.8, 1.15),
            rounding=18.0,
            fade=18.0,
            col=(1.0, 1.0, 1.0, 0.94),
        ),
    )
    draw_list.add_rect(image_min, image_max, _col(1.0, 1.0, 1.0, 0.28), 18.0, thickness=1.2)
    emit(
        draw_list,
        fxe.shimmer_band(
            image_min,
            image_max,
            rounding=18.0,
            progress=_cycle(item_id, "shader_image_shimmer", 2.2),
            width=0.22,
            intensity=0.28,
            angle=math.radians(18.0),
        ),
    )


def _draw_demo_card(index: int, title: str, desc: str, draw_fn) -> None:
    draw_list = imgui.get_window_draw_list()
    x, y = imgui.get_cursor_screen_pos()

    # 头部高度按当前字号自适应(14px 字体下与原固定布局一致, 大字体宿主
    # 如 Blender addon 的 30px 字体下头部自动加高, 预览区不再压住标题)。
    font = imgui.get_font()
    font_size = imgui.get_font_size()
    header_h = max(_GALLERY_PREVIEW_PAD_Y, font_size + 22.0)
    card_h = header_h + _GALLERY_PREVIEW_HEIGHT + 8.0
    text_top = y + 12.0
    clip_bottom = y + header_h - 4.0

    p_min = (x, y)
    p_max = (x + _GALLERY_CARD_WIDTH, y + card_h)

    draw_list.add_rect_filled(p_min, p_max, _col(0.055, 0.065, 0.082, 0.92), 16.0)
    draw_list.add_rect(p_min, p_max, _col(0.34, 0.50, 0.62, 0.22), 16.0, thickness=1.0)

    badge_text = f"{index:02d}"
    badge_pad = 6.0
    badge_w = imgui.calc_text_size(badge_text)[0] + badge_pad * 2.0
    draw_list.add_rect_filled(
        (x + 14.0, y + 10.0),
        (x + 14.0 + badge_w, y + 10.0 + font_size + 6.0),
        _col(0.16, 0.27, 0.38, 1.0),
        8.0,
    )
    draw_list.add_text(
        font,
        font_size,
        (x + 14.0 + badge_pad, text_top + 1.0),
        _col(0.80, 0.92, 1.0, 1.0),
        badge_text,
    )

    title_x = x + 14.0 + badge_w + 10.0
    desc_width = imgui.calc_text_size(desc)[0]
    desc_x = max(title_x, x + _GALLERY_CARD_WIDTH - 12.0 - desc_width)
    draw_list.add_text(
        font,
        font_size,
        (title_x, text_top),
        imgui.COL32_WHITE,
        title,
        0.0,
        (title_x, y + 10.0, desc_x - 8.0, clip_bottom),
    )
    draw_list.add_text(
        font,
        font_size,
        (desc_x, text_top),
        _col(0.64, 0.70, 0.78, 1.0),
        desc,
        0.0,
        (desc_x, y + 10.0, x + _GALLERY_CARD_WIDTH - 8.0, clip_bottom),
    )

    preview_pos = (x + _GALLERY_PREVIEW_PAD_X, y + header_h)
    imgui.set_cursor_screen_pos(preview_pos)
    draw_fn(preview_pos)

    imgui.set_cursor_screen_pos((x, y + card_h + _GALLERY_CARD_GAP - 1.0))
    imgui.dummy((_GALLERY_CARD_WIDTH, 1.0))


def _gallery_column_count(item_count: int) -> int:
    avail_width = imgui.get_content_region_avail()[0]
    column_width = _GALLERY_CARD_WIDTH + _GALLERY_CARD_GAP
    return max(1, min(item_count, int((avail_width + _GALLERY_CARD_GAP) // column_width)))


def _draw_demo_grid(table_id: str, demos, first_index: int) -> int:
    column_count = _gallery_column_count(len(demos))
    table_flags = imgui.TableFlags.SIZING_FIXED_FIT
    table_width = column_count * (_GALLERY_CARD_WIDTH + _GALLERY_CARD_GAP)
    if imgui.begin_table(table_id, column_count, table_flags, inner_width=table_width):
        for column_i in range(column_count):
            imgui.table_setup_column(
                f"column_{column_i}",
                imgui.TableColumnFlags.WIDTH_FIXED,
                _GALLERY_CARD_WIDTH + _GALLERY_CARD_GAP,
            )
        for demo_i, (title, desc, draw_fn) in enumerate(demos):
            if demo_i % column_count == 0:
                imgui.table_next_row()
            if imgui.table_set_column_index(demo_i % column_count):
                _draw_demo_card(first_index + demo_i, title, desc, draw_fn)
        imgui.end_table()
    return first_index + len(demos)


def draw_gallery(texture_id: int) -> None:
    draw_list = imgui.get_window_draw_list()
    io = imgui.get_io()
    fps = io.framerate
    frame_ms = 1000.0 / fps if fps > 0.0 else 0.0

    imgui.text("slimgui 特效画廊")
    imgui.same_line()
    imgui.text_disabled(f"性能: {fps:.1f} FPS / {frame_ms:.2f} ms")
    imgui.text_disabled("全部 fragfx 预设与 showcase 组合示例。")
    imgui.separator()

    non_interactive_demos = [
        (
            "shader_shimmer_band",
            "shader 扫光。",
            lambda pos: _draw_shader_shimmer_band(draw_list, pos, anim.hash_str("demo_shader_shimmer")),
        ),
        (
            "shader_radial_gleam",
            "shader 光斑。",
            lambda pos: _draw_shader_radial_gleam(draw_list, pos, anim.hash_str("demo_shader_radial_gleam")),
        ),
        (
            "shader_glass_pad",
            "材质垫: 光泽预设。",
            lambda pos: _draw_shader_glass_pad(draw_list, pos, anim.hash_str("demo_shader_glass_pad")),
        ),
        (
            "shader_metal_pad",
            "材质垫: 金属预设。",
            lambda pos: _draw_shader_metal_pad(draw_list, pos, anim.hash_str("demo_shader_metal_pad")),
        ),
        (
            "shader_rounded_rect_glint",
            "shader 流光。",
            lambda pos: _draw_shader_rounded_rect_glint(draw_list, pos, anim.hash_str("demo_shader_glint")),
        ),
        (
            "shader_corner_glints",
            "shader 四角扫光。",
            lambda pos: _draw_shader_corner_glints(draw_list, pos, anim.hash_str("demo_shader_corner_glints")),
        ),
        (
            "shader_soft_glow_rect",
            "shader 外发光。",
            lambda pos: _draw_shader_soft_glow_rect(draw_list, pos, anim.hash_str("demo_shader_soft_glow")),
        ),
        (
            "shader_rounded_rect_border_glow",
            "shader 边框光。",
            lambda pos: _draw_shader_rounded_rect_border_glow(draw_list, pos, anim.hash_str("demo_shader_border_glow")),
        ),
        (
            "shader_neon_tube_border",
            "shader 霓虹边框。",
            lambda pos: _draw_shader_neon_tube_border(draw_list, pos, anim.hash_str("demo_shader_neon_tube_border")),
        ),
        (
            "shader_rainbow_border",
            "shader 彩虹边框。",
            lambda pos: _draw_shader_rainbow_border(draw_list, pos, anim.hash_str("demo_shader_rainbow_border")),
        ),
        (
            "shader_inner_glow_rect",
            "shader 内柔光。",
            lambda pos: _draw_shader_inner_glow_rect(draw_list, pos, anim.hash_str("demo_shader_inner_glow")),
        ),
        (
            "shader_focus_ring",
            "shader 焦点环。",
            lambda pos: _draw_shader_focus_ring(draw_list, pos, anim.hash_str("demo_shader_focus_ring")),
        ),
        (
            "shader_rounded_image_edge_fade",
            "shader 纹理淡出。",
            lambda pos: _draw_shader_rounded_image_edge_fade(draw_list, pos, texture_id, anim.hash_str("demo_shader_image_fade")),
        ),
        (
            "shader_state_transition_glow",
            "shader 状态边光。",
            lambda pos: _draw_shader_state_transition_glow(draw_list, pos, anim.hash_str("demo_shader_state_transition_glow")),
        ),
        (
            "shader_path_particles",
            "shader 路径粒子。",
            lambda pos: _draw_shader_path_particles(draw_list, pos, anim.hash_str("demo_shader_path_particles")),
        ),
        (
            "shader_trail_dots",
            "shader 直线尾迹。",
            lambda pos: _draw_shader_trail_dots(draw_list, pos, anim.hash_str("demo_shader_trail_dots")),
        ),
    ]

    interactive_demos = [
        (
            "shader_click_ripple",
            "shader 涟漪。",
            lambda pos: _draw_shader_click_ripple(draw_list, pos, anim.hash_str("demo_shader_click_ripple")),
        ),
        (
            "shader_water_ripple",
            "点击折射水波: 噪波波前。",
            lambda pos: _draw_shader_water_ripple(draw_list, pos, texture_id, anim.hash_str("demo_shader_water_ripple")),
        ),
        (
            "shader_press_flash",
            "shader 按压闪光。",
            lambda pos: _draw_shader_press_flash(draw_list, pos, anim.hash_str("demo_shader_press_flash")),
        ),
        (
            "shader_shockwave",
            "shader 冲击波。",
            lambda pos: _draw_shader_shockwave(draw_list, pos, anim.hash_str("demo_shader_shockwave")),
        ),
        (
            "shader_magnetic_edge_glow",
            "shader 磁吸边光。",
            lambda pos: _draw_shader_magnetic_edge_glow(draw_list, pos, anim.hash_str("demo_shader_magnetic_edge_glow")),
        ),
        (
            "shader_spark_burst",
            "shader 爆发火花。",
            lambda pos: _draw_shader_spark_burst(draw_list, pos, anim.hash_str("demo_shader_spark_burst")),
        ),
    ]

    preview_size = (_GALLERY_PREVIEW_WIDTH, _GALLERY_PREVIEW_HEIGHT)
    showcase_demos = [
        (
            title,
            desc,
            lambda pos, fn=fn: fn(draw_list, pos, preview_size),
        )
        for title, desc, fn in showcase.SHOWCASE_DEMOS
    ]

    sections = [
        ("非交互", "自动循环，无需鼠标输入。", non_interactive_demos),
        ("交互", "点击或悬停预览触发反馈。", interactive_demos),
        ("Showcase 组合炫技", "纯词汇组合实现, 旧 mode 系统无法表达的效果。", showcase_demos),
    ]
    next_index = 1
    for section_i, (title, desc, demos) in enumerate(sections):
        if not demos:
            continue
        if section_i > 0:
            imgui.dummy((1.0, 8.0))
            imgui.separator()
        imgui.text(title)
        imgui.text_disabled(f"{desc}共 {len(demos)} 个示例。")
        next_index = _draw_demo_grid(f"##vfx_gallery_{section_i}", demos, next_index)


def main():
    import glfw
    import OpenGL.GL as gl
    from fragfx_renderer import VfxShaderGlfwRenderer

    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(1900, 960, "slimgui vfx gallery", None, None)
    glfw.make_context_current(window)
    glfw.swap_interval(0)

    imgui.create_context()
    load_chinese_font()
    renderer = VfxShaderGlfwRenderer(window)
    renderer.renderer.warmup(showcase.showcase_templates())
    texture_id = _create_checker_texture()
    showcase.set_demo_texture(texture_id)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        gl.glClearColor(0.045, 0.048, 0.060, 1.0)
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))

        renderer.new_frame()
        imgui.new_frame()
        anim.update_begin_frame()

        imgui.set_next_window_size((1840, 900), imgui.Cond.FIRST_USE_EVER)
        imgui.begin("VFX Gallery")
        draw_gallery(texture_id)
        imgui.end()

        imgui.render()
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    gl.glDeleteTextures([texture_id])
    renderer.shutdown()
    imgui.destroy_context(None)


if __name__ == "__main__":
    main()
