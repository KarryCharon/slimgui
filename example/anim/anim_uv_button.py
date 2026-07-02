import pathlib
from dataclasses import dataclass, field

import glfw
import OpenGL.GL as gl
import OpenImageIO as oiio

from util import load_chinese_font, emit
from slimgui import anim, imgui
from fragfx import effects as fxe
from fragfx_renderer import VfxShaderGlfwRenderer

ASSET_DIR = pathlib.Path(__file__).resolve().parent
PATTERN_PATH = ASSET_DIR / "seamless.png"
_UV_SCROLLS: dict[int, float] = {}

STRIP_HEIGHT = 28.0
HANDLE_HEIGHT = 10.0
HANDLE_HIT_RADIUS = 9.0
MAX_STOPS = 16


RGBA = tuple[float, float, float, float]


@dataclass(eq=False)
class GradientStop:
    pos: float
    color: RGBA


class GediantEditor:
    selected: int = 0
    drag_stop: GradientStop | None = None


def _default_stops() -> list[GradientStop]:
    return [
        GradientStop(0.3, (1.0, 1.0, 1.0, 1.0)),
        GradientStop(0.7, (1.0, 1.0, 1.0, 0.1)),
        GradientStop(0.8, (1.0, 1.0, 1.0, 0.0)),
    ]


@dataclass
class GradientParams:
    pattern_scale: float = 360.0
    angle_degrees: float = 230.0
    stops: list[GradientStop] = field(default_factory=_default_stops)

    def vfx_stops(self) -> list[tuple[float, RGBA]]:
        ordered = sorted(self.stops, key=lambda stop: stop.pos)
        return [(stop.pos, stop.color) for stop in ordered]


def _sort_stops(stops: list[GradientStop]) -> None:
    stops.sort(key=lambda stop: stop.pos)


def _find_stop(stops: list[GradientStop], stop: GradientStop | None) -> int:
    if stop is None:
        return -1
    for i, candidate in enumerate(stops):
        if candidate is stop:
            return i
    return -1


def _sample_rgba(stops: list[GradientStop], t: float) -> RGBA:
    ordered = sorted(stops, key=lambda stop: stop.pos)
    if t <= ordered[0].pos:
        return ordered[0].color
    if t >= ordered[-1].pos:
        return ordered[-1].color
    for i in range(len(ordered) - 1):
        left = ordered[i]
        right = ordered[i + 1]
        if left.pos <= t <= right.pos:
            span = right.pos - left.pos
            if span <= 0.0:
                return right.color
            u = (t - left.pos) / span
            return tuple(left.color[j] + (right.color[j] - left.color[j]) * u for j in range(4))
    return ordered[-1].color


def _mouse_t_on_strip(x0: float, width: float) -> float:
    mouse_x = imgui.get_io().mouse_pos[0]
    t = (mouse_x - x0) / max(width, 1.0)
    return min(max(t, 0.0), 1.0)


def _hit_stop_index(stops: list[GradientStop], x0: float, width: float, mouse_x: float) -> int:
    best = -1
    best_dist = HANDLE_HIT_RADIUS
    for i, stop in enumerate(stops):
        center_x = x0 + stop.pos * width
        dist = abs(mouse_x - center_x)
        if dist <= best_dist:
            best_dist = dist
            best = i
    return best


def _clamp_stop_pos(t: float) -> float:
    return min(max(t, 0.0), 1.0)


def _add_stop_at(params: GradientParams, t: float) -> int:
    t = min(max(t, 0.01), 0.99)
    for stop in params.stops:
        if abs(stop.pos - t) < 0.02:
            return _find_stop(params.stops, stop)
    new_stop = GradientStop(t, _sample_rgba(params.stops, t))
    params.stops.append(new_stop)
    _sort_stops(params.stops)
    return _find_stop(params.stops, new_stop)


def _remove_stop(params: GradientParams, index: int) -> None:
    if index <= 0 or index >= len(params.stops) - 1 or len(params.stops) <= 2:
        return
    params.stops.pop(index)


def _largest_gap_center(stops: list[GradientStop]) -> float:
    ordered = sorted(stops, key=lambda stop: stop.pos)
    best_gap = 0.0
    best_center = 0.5
    for i in range(len(ordered) - 1):
        gap = ordered[i + 1].pos - ordered[i].pos
        if gap > best_gap:
            best_gap = gap
            best_center = (ordered[i].pos + ordered[i + 1].pos) * 0.5
    return best_center


def _draw_gradient_strip_fill(
    draw_list: imgui.DrawList,
    p_min: tuple[float, float],
    p_max: tuple[float, float],
    stops: list[GradientStop],
) -> None:
    width = p_max[0] - p_min[0]
    segments = max(48, int(width))
    for segment_i in range(segments):
        t0 = segment_i / segments
        t1 = (segment_i + 1) / segments
        x0 = p_min[0] + t0 * width
        x1 = p_min[0] + t1 * width
        col0 = _col(*_sample_rgba(stops, t0))
        col1 = _col(*_sample_rgba(stops, t1))
        draw_list.add_rect_filled_multi_color((x0, p_min[1]), (x1, p_max[1]), col0, col1, col1, col0)


def _draw_stop_handle(
    draw_list: imgui.DrawList,
    center_x: float,
    strip_top: float,
    strip_bottom: float,
    selected: bool,
) -> None:
    fill = _col(1.0, 0.86, 0.2, 1.0) if selected else _col(1.0, 1.0, 1.0, 0.95)
    outline = _col(0.0, 0.0, 0.0, 0.85)
    tip_y = strip_top - HANDLE_HEIGHT
    draw_list.add_triangle_filled(
        (center_x, tip_y),
        (center_x - 6.0, strip_top),
        (center_x + 6.0, strip_top),
        fill,
    )
    draw_list.add_triangle(
        (center_x, tip_y),
        (center_x - 6.0, strip_top),
        (center_x + 6.0, strip_top),
        outline,
        1.0,
    )
    draw_list.add_line((center_x, strip_top), (center_x, strip_bottom), fill, 2.0)


def _draw_gradient_strip_editor(params: GradientParams) -> None:
    draw_list = imgui.get_window_draw_list()
    strip_width = imgui.calc_item_width()
    total_height = STRIP_HEIGHT + HANDLE_HEIGHT
    p_min = imgui.get_cursor_screen_pos()
    strip_top = p_min[1] + HANDLE_HEIGHT
    strip_bottom = strip_top + STRIP_HEIGHT
    p_strip_max = (p_min[0] + strip_width, strip_bottom)

    _draw_gradient_strip_fill(draw_list, (p_min[0], strip_top), p_strip_max, params.stops)
    draw_list.add_rect(
        (p_min[0], strip_top),
        p_strip_max,
        _col(0.45, 0.45, 0.45, 1.0),
        0.0,
        thickness=1.0,
    )

    selected = GediantEditor.selected
    for i, stop in enumerate(params.stops):
        center_x = p_min[0] + stop.pos * strip_width
        _draw_stop_handle(draw_list, center_x, strip_top, strip_bottom, i == selected)

    imgui.invisible_button("##gradient_strip", (strip_width, total_height))
    io = imgui.get_io()
    mouse_x = io.mouse_pos[0]

    drag_stop = GediantEditor.drag_stop
    if drag_stop is None and imgui.is_item_hovered():
        if imgui.is_mouse_clicked(imgui.MouseButton.LEFT):
            hit = _hit_stop_index(params.stops, p_min[0], strip_width, mouse_x)
            if hit >= 0:
                GediantEditor.selected = hit
                GediantEditor.drag_stop = params.stops[hit]
            elif len(params.stops) < MAX_STOPS:
                t = _mouse_t_on_strip(p_min[0], strip_width)
                if 0.02 < t < 0.98:
                    GediantEditor.selected = _add_stop_at(params, t)

        if imgui.is_mouse_double_clicked(imgui.MouseButton.LEFT):
            hit = _hit_stop_index(params.stops, p_min[0], strip_width, mouse_x)
            if 0 < hit < len(params.stops) - 1 and len(params.stops) > 2:
                removed = params.stops[hit]
                _remove_stop(params, hit)
                if GediantEditor.drag_stop is removed:
                    GediantEditor.drag_stop = None
                GediantEditor.selected = min(hit, len(params.stops) - 1)

    drag_stop = GediantEditor.drag_stop
    if drag_stop is not None and imgui.is_mouse_down(imgui.MouseButton.LEFT):
        drag_index = _find_stop(params.stops, drag_stop)
        if drag_index < 0:
            GediantEditor.drag_stop = None
        else:
            t = _mouse_t_on_strip(p_min[0], strip_width)
            drag_stop.pos = _clamp_stop_pos(t)
            _sort_stops(params.stops)
            GediantEditor.selected = _find_stop(params.stops, drag_stop)
    elif imgui.is_mouse_released(imgui.MouseButton.LEFT):
        GediantEditor.drag_stop = None

    if imgui.small_button("添加停靠点") and len(params.stops) < MAX_STOPS:
        GediantEditor.selected = _add_stop_at(params, _largest_gap_center(params.stops))
    imgui.same_line()
    can_delete = 0 < GediantEditor.selected < len(params.stops) - 1 and len(params.stops) > 2
    if not can_delete:
        imgui.begin_disabled()
    if imgui.small_button("删除选中") and can_delete:
        removed = params.stops[GediantEditor.selected]
        _remove_stop(params, GediantEditor.selected)
        if GediantEditor.drag_stop is removed:
            GediantEditor.drag_stop = None
        GediantEditor.selected = min(GediantEditor.selected, len(params.stops) - 1)
    if not can_delete:
        imgui.end_disabled()

    selected: int = GediantEditor.selected
    if 0 <= selected < len(params.stops):
        stop = params.stops[selected]
        _, stop.pos = imgui.slider_float("位置", stop.pos, 0.0, 1.0, "%.2f")
        stop.pos = _clamp_stop_pos(stop.pos)
        _sort_stops(params.stops)
        found = _find_stop(params.stops, stop)
        if found >= 0:
            GediantEditor.selected = found
        _, stop.color = imgui.color_edit4(
            "颜色",
            stop.color,
            imgui.ColorEditFlags.FLOAT,
        )


def _col(r: float, g: float, b: float, a: float) -> int:
    return imgui.get_color_u32((r, g, b, a))


def _inset_rect(
    p_min: tuple[float, float],
    p_max: tuple[float, float],
    inset: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        (p_min[0] + inset, p_min[1] + inset),
        (p_max[0] - inset, p_max[1] - inset),
    )


def _read_png_rgba(path: pathlib.Path) -> tuple[int, int, bytes]:
    image_input = oiio.ImageInput.open(str(path))
    if image_input is None:
        raise ValueError(oiio.geterror() or f"Failed to open image: {path}")

    try:
        spec = image_input.spec()
        pixels = image_input.read_image(format=oiio.UINT8)
        if pixels is None:
            raise ValueError(image_input.geterror() or f"Failed to read image: {path}")
    finally:
        image_input.close()

    raw = pixels.tobytes()
    channels = spec.nchannels
    if channels == 4:
        return spec.width, spec.height, raw

    rgba = bytearray(spec.width * spec.height * 4)
    for pixel_i in range(spec.width * spec.height):
        src = pixel_i * channels
        dst = pixel_i * 4
        red = raw[src]
        green = raw[src + 1] if channels > 1 else red
        blue = raw[src + 2] if channels > 2 else red
        alpha = raw[src + 3] if channels > 3 else 255
        rgba[dst : dst + 4] = (red, green, blue, alpha)

    return spec.width, spec.height, bytes(rgba)


def _as_white_alpha_mask(pixels: bytes) -> bytes:
    masked = bytearray(len(pixels))
    for i in range(0, len(pixels), 4):
        alpha = max(pixels[i], pixels[i + 1], pixels[i + 2]) * pixels[i + 3] // 255
        masked[i : i + 4] = (255, 255, 255, alpha)
    return bytes(masked)


def _create_repeat_texture(path: pathlib.Path) -> int:
    width, height, pixels = _read_png_rgba(path)
    pixels = _as_white_alpha_mask(pixels)
    tex_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, pixels)
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
    return tex_id


def _draw_gradient_params_panel(params: GradientParams) -> None:
    imgui.separator()
    imgui.text("图案参数")
    _, params.pattern_scale = imgui.slider_float("图案缩放", params.pattern_scale, 10.0, 800.0, "%.0f")
    imgui.text("渐变参数")
    _, params.angle_degrees = imgui.slider_float("角度", params.angle_degrees, 0.0, 360.0, "%.0f°")
    _draw_gradient_strip_editor(params)


def uv_pattern_button(
    label: str,
    size: tuple[float, float],
    texture_id: int,
    gradient: GradientParams,
) -> bool:
    draw_list = imgui.get_window_draw_list()
    pos = imgui.get_cursor_screen_pos()
    clicked = imgui.invisible_button(f"##{label}", size)
    hovered = imgui.is_item_hovered()
    item_id = anim.hash_str(label)
    io = imgui.get_io()

    x, y = pos
    w, h = size
    rounding = h * 0.5
    p_min = (x, y)
    p_max = (x + w, y + h)

    uv_scroll = _UV_SCROLLS.get(item_id, 0.0)
    if hovered:
        uv_scroll = (uv_scroll + io.delta_time / 4.6) % 1.0
        _UV_SCROLLS[item_id] = uv_scroll
    body_color = (174.0 / 255.0, 218.0 / 255.0, 2.0 / 255.0, 1.0)
    face_color = _col(*body_color)

    scale = h / 86.0
    gray_inset = 3.0 * scale
    light_inset = 6.0 * scale
    face_inset = 12.0 * scale
    gray_min, gray_max = _inset_rect(p_min, p_max, gray_inset)
    light_min, light_max = _inset_rect(p_min, p_max, light_inset)
    face_min, face_max = _inset_rect(p_min, p_max, face_inset)
    gray_rounding = max(0.0, rounding - gray_inset)
    light_rounding = max(0.0, rounding - light_inset)
    face_rounding = max(0.0, rounding - face_inset)

    draw_list.add_rect_filled((x + 1.5, y + 2.0), (x + w + 1.5, y + h + 3.0), _col(0.0, 0.0, 0.0, 0.16), rounding)
    draw_list.add_rect_filled(p_min, p_max, _col(0.0, 0.0, 0.0, 1.0), rounding)
    draw_list.add_rect_filled(gray_min, gray_max, _col(56.0 / 255.0, 64.0 / 255.0, 78.0 / 255.0, 1.0), gray_rounding)
    draw_list.add_rect_filled(light_min, light_max, face_color, light_rounding)
    draw_list.add_rect_filled(light_min, light_max, _col(1.0, 1.0, 1.0, 0.30), light_rounding)
    draw_list.add_rect_filled(face_min, face_max, face_color, face_rounding)

    pattern_left = p_min[0] + (p_max[0] - p_min[0]) * 0.56
    pattern_min = (pattern_left, p_min[1])
    pattern_max = p_max
    pattern_w = pattern_max[0] - pattern_min[0]
    pattern_h = pattern_max[1] - pattern_min[1]
    emit(
        draw_list,
        fxe.rounded_image_linear_gradient(
            texture_id,
            pattern_min,
            pattern_max,
            (0.10, -uv_scroll),
            (0.10 + pattern_w / gradient.pattern_scale, pattern_h / gradient.pattern_scale - uv_scroll),
            angle_degrees=gradient.angle_degrees,
            stops=gradient.vfx_stops(),
            rounding=rounding,
            flags=imgui.DrawFlags.ROUND_CORNERS_RIGHT,
        ),
    )

    return clicked


def main():
    glfw.init()
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(760, 520, "slimgui textured capsule button", None, None)
    glfw.make_context_current(window)
    glfw.swap_interval(0)

    imgui.create_context()
    load_chinese_font()
    renderer = VfxShaderGlfwRenderer(window)
    texture_id = _create_repeat_texture(PATTERN_PATH)
    gradient_params = GradientParams()

    while not glfw.window_should_close(window):
        glfw.poll_events()
        gl.glClearColor(24.0 / 255.0, 24.0 / 255.0, 24.0 / 255.0, 1.0)
        gl.glClear(int(gl.GL_COLOR_BUFFER_BIT) | int(gl.GL_DEPTH_BUFFER_BIT))

        renderer.new_frame()
        imgui.new_frame()
        anim.update_begin_frame()

        imgui.set_next_window_size((700, 440), imgui.Cond.FIRST_USE_EVER)
        imgui.push_style_color(imgui.Col.WINDOW_BG, (24.0 / 255.0, 24.0 / 255.0, 24.0 / 255.0, 1.0))
        imgui.begin("Textured capsule button")
        uv_pattern_button("run_capsule", (620, 131), texture_id, gradient_params)
        _draw_gradient_params_panel(gradient_params)
        imgui.end()
        imgui.pop_style_color()

        imgui.render()
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    gl.glDeleteTextures([texture_id])
    renderer.shutdown()
    imgui.destroy_context(None)


if __name__ == "__main__":
    main()
