"""Preset effects: each helper builds a frozen `Effect` from a cached
`Template` (structure built once, named uniforms rebound per call)."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from . import blocks
from . import math as fxm
from .color import hsv2rgb, rgba, tex
from .core.nodes import FRAG, Point, Vec
from .core.template import Effect, Template, TemplateParams
from .fields import ROUND_CORNERS_ALL, RoundedRect, rounded_rect_sdf_flags
from .lib import MAX_PARTICLES
from .profiles import edge_profile, gauss, piecewise_linear, smoothfall, tent, wrap_delta

RGBA = tuple[float, float, float, float]

__all__ = [
    "TemplateStore",
    "preset_templates",
    "glass_pad",
    "metal_pad",
    "shimmer_band",
    "soft_glow_rect",
    "inner_glow_rect",
    "focus_ring",
    "radial_gleam",
    "click_ripple",
    "shockwave",
    "press_flash",
    "rounded_rect_border_glow",
    "neon_tube_border",
    "rainbow_border",
    "state_transition_glow",
    "magnetic_edge_glow",
    "rounded_rect_glint",
    "corner_glints",
    "rounded_image_edge_fade",
    "rounded_image_linear_gradient",
    "path_particles",
    "spark_burst",
    "trail_dots",
]


# -- small Python-side helpers ------------------------------------------------


def _rgba(color: RGBA) -> RGBA:
    return (float(color[0]), float(color[1]), float(color[2]), float(color[3]))


def _point(p: Point) -> Point:
    return (float(p[0]), float(p[1]))


def _pad(p_min: Point, p_max: Point, pad: float) -> tuple[Point, Point]:
    return (p_min[0] - pad, p_min[1] - pad), (p_max[0] + pad, p_max[1] + pad)


def _clamp01(x: float) -> float:
    return min(max(float(x), 0.0), 1.0)


def _s01(edge0: float, edge1: float, x: float) -> float:
    t = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def _max_inner(p_min: Point, p_max: Point) -> float:
    size = min(p_max[0] - p_min[0], p_max[1] - p_min[1])
    return max(size * 0.5 - 0.5, 1.0)


_MAX_GRADIENT_STOPS = 16


def _normalize_gradient_stops(stops: Sequence[tuple[float, RGBA]]) -> tuple[tuple[float, RGBA], ...]:
    parsed = sorted(((float(pos), _rgba(col)) for pos, col in stops), key=lambda stop: stop[0])
    if not parsed:
        return ((0.0, (1.0, 1.0, 1.0, 1.0)),)
    return tuple(parsed[:_MAX_GRADIENT_STOPS])


def _rounded_rect_sdf_py(p: Point, p_min: Point, p_max: Point, rounding: float) -> float:
    cx, cy = (p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5
    hx, hy = (p_max[0] - p_min[0]) * 0.5, (p_max[1] - p_min[1]) * 0.5
    r = max(0.0, min(rounding, min(hx, hy)))
    qx = abs(p[0] - cx) - (hx - r)
    qy = abs(p[1] - cy) - (hy - r)
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    return outside + min(max(qx, qy), 0.0) - r


def _boundary_anchor(p_min: Point, p_max: Point, rounding: float, pointer: Point) -> Point:
    """Boundary point where the center-to-pointer ray exits the rounded rect."""
    cx, cy = (p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5
    dx, dy = pointer[0] - cx, pointer[1] - cy
    n = math.hypot(dx, dy)
    if n < 1e-6:
        dx, dy, n = 1.0, 0.0, 1.0
    dx, dy = dx / n, dy / n
    lo, hi = 0.0, math.hypot(p_max[0] - p_min[0], p_max[1] - p_min[1])
    for _ in range(24):
        mid = (lo + hi) * 0.5
        if _rounded_rect_sdf_py((cx + dx * mid, cy + dy * mid), p_min, p_max, rounding) <= 0.0:
            lo = mid
        else:
            hi = mid
    return (cx + dx * lo, cy + dy * lo)


def _rect_path_params(p_min: Point, p_max: Point, rounding: float, p: Point) -> tuple[float, float]:
    """Perimeter parameterization of `p` near the border; mirrors rect_path_t.

    Returns (path_t in [0, 1), perimeter length in pixels).
    """
    w, h = p_max[0] - p_min[0], p_max[1] - p_min[1]
    r = max(0.0, min(rounding, min(w, h) * 0.5))
    top_len = max(w - 2.0 * r, 0.0)
    side_len = max(h - 2.0 * r, 0.0)
    arc_len = math.pi * r * 0.5
    per = 2.0 * top_len + 2.0 * side_len + 4.0 * arc_len
    if per <= 0.0:
        return 0.0, 1.0

    icx0, icy0 = p_min[0] + r, p_min[1] + r
    icx1, icy1 = p_max[0] - r, p_max[1] - r
    corner_x = p[0] < icx0 or p[0] > icx1
    corner_y = p[1] < icy0 or p[1] > icy1

    if corner_x and corner_y and r > 0.0:
        right = p[0] > icx1
        bottom = p[1] > icy1
        ccx = icx1 if right else icx0
        ccy = icy1 if bottom else icy0
        a = math.atan2(p[1] - ccy, p[0] - ccx)
        half_pi = math.pi * 0.5
        if right and not bottom:
            s = top_len + (a + half_pi) / half_pi * arc_len
        elif right and bottom:
            s = top_len + arc_len + side_len + a / half_pi * arc_len
        elif not right and bottom:
            s = 2.0 * top_len + 2.0 * arc_len + side_len + (a - half_pi) / half_pi * arc_len
        else:
            s = 2.0 * top_len + 3.0 * arc_len + 2.0 * side_len + (a + math.pi) / half_pi * arc_len
    else:
        dt, db = p[1] - p_min[1], p_max[1] - p[1]
        dl, dr = p[0] - p_min[0], p_max[0] - p[0]
        m = min(dt, db, dl, dr)
        if m == dt:
            s = min(max(p[0] - icx0, 0.0), top_len)
        elif m == dr:
            s = top_len + arc_len + min(max(p[1] - icy0, 0.0), side_len)
        elif m == db:
            s = top_len + 2.0 * arc_len + side_len + min(max(icx1 - p[0], 0.0), top_len)
        else:
            s = 2.0 * top_len + 3.0 * arc_len + side_len + min(max(icy1 - p[1], 0.0), side_len)
    return (s / per) % 1.0, per


def _mesh_clip_softness(w: float, h: float) -> float:
    nx = max(12, min(128, math.ceil(w / 2.0)))
    ny = max(12, min(128, math.ceil(h / 2.0)))
    cell_w = w / nx if nx > 0 else w
    cell_h = h / ny if ny > 0 else h
    return max(1.0, math.hypot(cell_w, cell_h) * 0.5)


def _gradient_proj_range(p_min: Point, p_max: Point, angle_degrees: float) -> tuple[float, float]:
    angle = math.radians(angle_degrees)
    dir_x = math.sin(angle)
    dir_y = math.cos(angle)
    corners = (
        (p_min[0], p_min[1]),
        (p_max[0], p_min[1]),
        (p_max[0], p_max[1]),
        (p_min[0], p_max[1]),
    )
    projs = [corner[0] * dir_x + corner[1] * dir_y for corner in corners]
    return min(projs), max(projs)


# -- template registry ---------------------------------------------------------


class TemplateStore:
    """Lazy cache of effect `Template`s, keyed by *structure* (helper name +
    structure-affecting config such as stop count). Presets registered with
    `add_preset` can be batch-built for renderer warmup."""

    def __init__(self):
        self._cache: dict[object, Template] = {}
        self._presets: list[tuple[object, Callable[..., Template], tuple[object, ...]]] = []

    def get(self, key: object, builder: "Callable[..., Template]", *args: object) -> Template:
        template = self._cache.get(key)
        if template is None:
            template = self._cache[key] = builder(*args)
        return template

    def add_preset(self, key: object, builder: "Callable[..., Template]", *args: object) -> None:
        self._presets.append((key, builder, args))

    def presets(self) -> list[Template]:
        return [self.get(key, builder, *args) for key, builder, args in self._presets]


_PRESETS = TemplateStore()


def _rect_params(p: TemplateParams) -> RoundedRect:
    return RoundedRect(p.vec2("p_min"), p.vec2("p_max"), p.f("rounding"))


# -- template builders -----------------------------------------------------------
# One builder per effect structure. Anonymous numbers inside the trees are
# frozen build-time constants; everything per-call goes through named params.


def _t_material() -> Template:
    p = TemplateParams()
    color = blocks.material_pad(
        p.vec2("p_min"), p.vec2("p_max"), p.f("rounding"), p.f("intensity"),
        p.vec4("tint"), p.f("thickness"), p.f("angle"), p.f("metallic"),
        p.f("roughness"), p.f("specular"), p.f("softness"),
    )
    return Template(color, p)


def _t_shimmer() -> Template:
    p = TemplateParams()
    p_min = p.vec2("p_min")
    rect = RoundedRect(p_min, p.vec2("p_max"), p.f("rounding"))
    u = (fxm.dot(FRAG - p_min, p.vec2("dir")) - p.f("center")) / p.f("half_band")
    alpha = rect.clip() * gauss(u, 2.6) * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_soft_glow() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    t = fxm.clamp(rect.sdf / p.f("spread"), 0.0, 1.0)
    alpha = smoothfall(t) * fxm.smooth01(-2.0, 0.0, rect.sdf) * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_inner_glow() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    t = fxm.clamp(-rect.sdf / p.f("spread"), 0.0, 1.0)
    alpha = smoothfall(t) * (1.0 - fxm.smooth01(0.0, 1.5, rect.sdf)) * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_focus_ring() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    alpha = tent((rect.sdf + p.f("inset")) / p.f("hw")) * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_border_glow() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    profile = piecewise_linear(
        -rect.sdf,
        [(p.f("x0"), 0.0), (p.f("x1"), 0.46), (0.0, 1.0), (p.f("x3"), 0.46), (p.f("x4"), 0.0)],
    )
    alpha = profile * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_neon() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    u = -rect.sdf
    nodes = [p.f("x0"), p.f("x1"), p.f("x2"), 0.0, p.f("x4"), p.f("x5"), p.f("x6")]
    g = piecewise_linear(u, list(zip(nodes, [0.0, 0.22, 0.58, 0.78, 0.58, 0.22, 0.0])))
    c = piecewise_linear(u, list(zip(nodes, [0.0, 0.0, 0.18, 1.0, 0.18, 0.0, 0.0])))
    col = fxm.mix(p.vec3("rgb"), p.vec3("core_rgb"), c)
    alpha = fxm.max(g, c) * p.f("alpha_scale")
    return Template(rgba(col, alpha), p)


def _t_rainbow() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    alpha = fxm.max(0.0, 1.0 - fxm.abs(rect.sdf) / p.f("hw")) * p.f("alpha_scale")
    col = hsv2rgb(fxm.fract(rect.path_t + p.f("progress")), 0.85, 1.0)
    return Template(rgba(col, alpha), p)


def _t_state_glow() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    alpha = edge_profile(-rect.sdf, p.f("w"), 0.82, 0.48, 0.18) * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_magnetic() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    profile = edge_profile(-rect.sdf, p.f("w"), 0.9, 0.58, 0.22)
    # True perimeter distance so the glow never leaks to the opposite edge.
    magnetic = 1.0 - fxm.smooth01(0.0, p.f("reach"), wrap_delta(rect.path_t, p.f("anchor_t")) * p.f("perimeter"))
    alpha = profile * magnetic * magnetic * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_glint(with_corner_colors: bool) -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    band = tent((rect.sdf + p.f("inset")) / p.f("hw"))
    sweep = fxm.pow(
        1.0 - fxm.smooth01(0.0, 1.0, wrap_delta(rect.path_t, p.f("progress")) / p.f("half_len")),
        p.f("inv_softness"),
    )
    if with_corner_colors:
        k = rect.uv(clamp01=True)
        col = fxm.mix(
            fxm.mix(p.vec4("col_tl"), p.vec4("col_tr"), k.x),
            fxm.mix(p.vec4("col_bl"), p.vec4("col_br"), k.x),
            k.y,
        )
    else:
        col = p.vec4("col")
    return Template(rgba(col.rgb, col.a * band * sweep), p)


def _t_corner_glints() -> Template:
    p = TemplateParams()
    half_pi = math.pi * 0.5
    # Light catching the four rounded corners of a glossy frame: a gaussian
    # arc highlight (bright core + soft bloom) sweeps through each corner
    # arc, whitening at its peak. Each pixel is shaded against its quadrant
    # corner; the endpoint window keeps the glint inside the arc.
    right = fxm.step(p.f("cx"), FRAG.x)
    bottom = fxm.step(p.f("cy"), FRAG.y)
    ccx = fxm.mix(p.f("ccx0"), p.f("ccx1"), right)
    ccy = fxm.mix(p.f("ccy0"), p.f("ccy1"), bottom)
    cc = Vec(ccx, ccy)

    # corner arcs: tl [-pi,-pi/2], tr [-pi/2,0], br [0,pi/2], bl [pi/2,pi]
    a = fxm.atan2(FRAG.y - ccy, FRAG.x - ccx)
    a_start = -math.pi + right * half_pi + bottom * (3.0 * half_pi) - (right * bottom) * math.pi
    local_t = (a - a_start) / half_pi

    rd = (fxm.length(FRAG - cc) - p.f("rc")) / p.f("hw")
    core = gauss(rd, 2.8)
    halo = 0.38 * gauss(rd, 0.45)
    sweep = gauss((local_t - p.f("progress")) / p.f("sigma"))
    endpoint = fxm.smooth01(-0.04, 0.18, local_t) * fxm.smooth01(-0.04, 0.18, 1.0 - local_t)

    alpha = (core + halo) * sweep * endpoint * p.f("alpha_scale")
    col = fxm.mix(p.vec3("rgb"), (1.0, 1.0, 1.0), core * sweep * 0.45)
    return Template(rgba(col, alpha), p)


def _t_gleam() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    d = (FRAG - p.vec2("center")) / p.vec2("radii")
    alpha = smoothfall(fxm.clamp(fxm.length(d), 0.0, 1.0)) * rect.clip() * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_ripple() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    ring_r = p.f("ring_r")
    front = p.f("front")
    dist = fxm.length(FRAG - p.vec2("center"))
    fill = 1.0 - fxm.smooth01(ring_r - front, ring_r, dist)
    et = fxm.abs(dist - (ring_r - front * 0.35)) / front
    edge = gauss(et, 4.5) * (1.0 - fxm.step(1.0, et))
    wave = fxm.clamp(fill * 0.36 + edge * 0.64, 0.0, 1.0)
    alpha = wave * rect.clip() * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_shockwave() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    t = fxm.abs(fxm.length(FRAG - p.vec2("center")) - p.f("ring_r")) / p.f("hw")
    ring = (1.0 - fxm.smooth01(0.15, 1.0, t)) * (1.0 - fxm.step(1.0, t))
    alpha = ring * ring * rect.clip() * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_flash() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    t = fxm.clamp(fxm.length(FRAG - p.vec2("center")) / p.f("flash_r"), 0.0, 1.0)
    alpha = smoothfall(t) * rect.clip() * p.f("alpha_scale")
    return Template(rgba(p.vec3("rgb"), alpha), p)


def _t_edge_fade(with_fade: bool) -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    uv = fxm.mix(p.vec2("uv_min"), p.vec2("uv_max"), rect.uv())
    sample = tex(uv)
    clip_alpha = 1.0 - fxm.smooth01(-0.5, 0.5, rect.sdf)
    alpha = p.f("col_a") * sample.a * clip_alpha
    if with_fade:
        alpha = alpha * fxm.mix(p.f("min_alpha"), 1.0, fxm.smooth01(0.0, p.f("fade"), -rect.sdf))
    return Template(rgba(p.vec3("rgb") * sample.rgb, alpha), p)


def _t_linear_gradient(n_stops: int, flags: int) -> Template:
    p = TemplateParams()
    p_min = p.vec2("p_min")
    p_max = p.vec2("p_max")
    rounding = p.f("rounding")
    rect = RoundedRect(p_min, p_max, rounding)
    uv = fxm.mix(p.vec2("uv_min"), p.vec2("uv_max"), rect.uv())
    sample = tex(uv)

    t = (fxm.dot(FRAG, p.vec2("dir")) - p.f("proj_min")) / p.f("proj_range")
    grad = p.vec4("c0")
    for i in range(1, n_stops):
        factor = fxm.clamp((t - p.f(f"pos{i - 1}")) / p.f(f"span{i}"), 0.0, 1.0)
        grad = fxm.mix(grad, p.vec4(f"c{i}"), factor)

    sdf = rounded_rect_sdf_flags(p_min, p_max, rounding, flags)
    cs = p.f("clip_softness")
    clip_alpha = 1.0 - fxm.smooth01(-cs, cs, sdf)
    color = rgba(sample.rgb * grad.rgb, sample.a * grad.a * clip_alpha)
    return Template(color, p)


def _t_particles_path() -> Template:
    p = TemplateParams()
    color = blocks.particles_path(
        p.vec2("p_min"), p.vec2("p_max"), p.f("rounding"), p.f("progress"),
        p.f("trail"), p.f("inset"), p.f("count"), p.f("radius"), p.f("intensity"), p.vec4("tint"),
    )
    return Template(color, p)


def _t_particles_burst() -> Template:
    p = TemplateParams()
    color = blocks.particles_burst(
        p.vec2("center"), p.f("progress"), p.f("count"), p.f("radius"),
        p.f("spread"), p.f("intensity"), p.vec4("tint"),
    )
    return Template(color, p)


def _t_particles_trail() -> Template:
    p = TemplateParams()
    color = blocks.particles_trail(
        p.vec2("start"), p.vec2("end"), p.f("progress"), p.f("count"),
        p.f("radius"), p.f("spacing"), p.f("intensity"), p.vec4("tint"),
    )
    return Template(color, p)


for _key, _builder, _args in (
    ("material", _t_material, ()),
    ("shimmer", _t_shimmer, ()),
    ("soft_glow", _t_soft_glow, ()),
    ("inner_glow", _t_inner_glow, ()),
    ("focus_ring", _t_focus_ring, ()),
    ("border_glow", _t_border_glow, ()),
    ("neon", _t_neon, ()),
    ("rainbow", _t_rainbow, ()),
    ("state_glow", _t_state_glow, ()),
    ("magnetic", _t_magnetic, ()),
    (("glint", False), _t_glint, (False,)),
    (("glint", True), _t_glint, (True,)),
    ("corner_glints", _t_corner_glints, ()),
    ("gleam", _t_gleam, ()),
    ("ripple", _t_ripple, ()),
    ("shockwave", _t_shockwave, ()),
    ("flash", _t_flash, ()),
    (("edge_fade", True), _t_edge_fade, (True,)),
    (("edge_fade", False), _t_edge_fade, (False,)),
    (("linear_gradient", 2, 240), _t_linear_gradient, (2, 240)),
    ("particles_path", _t_particles_path, ()),
    ("particles_burst", _t_particles_burst, ()),
    ("particles_trail", _t_particles_trail, ()),
):
    _PRESETS.add_preset(_key, _builder, *_args)


def preset_templates() -> list[Template]:
    """All preset structures, e.g. for renderer warmup at startup."""
    return _PRESETS.presets()


# -- material -----------------------------------------------------------------


def glass_pad(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    thickness: float = 14.0,
    intensity: float = 0.7,
    color: RGBA = (1.0, 1.0, 1.0, 1.0),
    angle: float = -0.7853981633974483,
    softness: float = 0.4,
) -> Effect:
    """
    Glossy dielectric preset of the `material` pad: a flat plateau with a
    convex shoulder of `thickness` pixels, lit by a directional light.

    The pad draws its own body in `color` (alpha = body opacity). `angle`
    is the light azimuth in radians (0 = from the top, negative rotates
    toward the top-left); `intensity` scales highlight/shadow strength.
    `softness` eases the shoulder-to-plateau transition (0 = visible
    crease, 1 = very gradual fillet).
    """
    p_min, p_max = _point(p_min), _point(p_max)
    return _PRESETS.get("material", _t_material).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding, intensity=intensity,
        tint=_rgba(color), thickness=thickness, angle=angle,
        metallic=0.0, roughness=0.25, specular=0.9, softness=softness,
    )


def metal_pad(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    thickness: float = 14.0,
    intensity: float = 0.7,
    color: RGBA = (0.83, 0.69, 0.22, 1.0),
    angle: float = -0.7853981633974483,
    roughness: float = 0.4,
    softness: float = 0.4,
) -> Effect:
    """
    Metallic preset of the `material` pad: tinted contrasty highlights and
    a stronger environment gradient on the plateau.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    return _PRESETS.get("material", _t_material).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding, intensity=intensity,
        tint=_rgba(color), thickness=thickness, angle=angle,
        metallic=1.0, roughness=roughness, specular=1.0, softness=softness,
    )


# -- directional band -----------------------------------------------------------


def shimmer_band(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    width: float = 0.28,
    intensity: float = 0.8,
    angle: float = 0.0,
    color: RGBA = (1.0, 1.0, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel highlight band sweeping across a rounded rect.

    `progress` moves the band across the rect along `angle` (radians).
    `width` is a fraction of the larger rect dimension.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    w, h = p_max[0] - p_min[0], p_max[1] - p_min[1]
    direction = (math.cos(angle), math.sin(angle))
    t0 = min(0.0, direction[0] * w) + min(0.0, direction[1] * h)
    t1 = max(0.0, direction[0] * w) + max(0.0, direction[1] * h)
    half_band = max(width * max(w, h) * 0.5, 1.0)
    center = (t0 - half_band) + ((t1 + half_band) - (t0 - half_band)) * (progress % 1.0)
    return _PRESETS.get("shimmer", _t_shimmer).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding, dir=direction,
        center=center, half_band=half_band,
        alpha_scale=intensity * color[3], rgb=color[:3],
    )


# -- SDF glow / border family -----------------------------------------------------


def soft_glow_rect(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    spread: float = 18.0,
    intensity: float = 0.45,
    color: RGBA = (0.35, 0.65, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel soft outer glow around a rounded rect.

    `spread` is the glow radius in pixels. Draw the glow before the filled
    surface when you want the center covered by the control itself.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    return _PRESETS.get("soft_glow", _t_soft_glow).effect(
        *_pad(p_min, p_max, spread + 2.0),
        p_min=p_min, p_max=p_max, rounding=rounding,
        spread=max(spread, 1.0), alpha_scale=intensity * color[3], rgb=color[:3],
    )


def inner_glow_rect(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    spread: float = 18.0,
    intensity: float = 0.45,
    color: RGBA = (0.35, 0.65, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel soft glow fading inward from the rounded rect edge.

    `spread` is the glow radius in pixels extending inward from the edge.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    return _PRESETS.get("inner_glow", _t_inner_glow).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding,
        spread=min(max(spread, 1.0), _max_inner(p_min, p_max)),
        alpha_scale=intensity * color[3], rgb=color[:3],
    )


def focus_ring(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    progress: float = 1.0,
    width: float = 4.0,
    inset: float = 0.0,
    color: RGBA = (0.45, 0.75, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel rounded focus indicator around a widget.

    `progress` controls the ring appearing (0 hidden, 1 fully visible).
    Positive `inset` moves the ring inside the rect, negative outside.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    appear = _s01(0.0, 1.0, _clamp01(progress))
    return _PRESETS.get("focus_ring", _t_focus_ring).effect(
        *_pad(p_min, p_max, max(0.0, width * 0.5 - inset) + 2.0),
        p_min=p_min, p_max=p_max, rounding=rounding, inset=inset,
        hw=max(width * (0.65 + 0.35 * appear) * 0.5, 0.5),
        alpha_scale=appear * color[3], rgb=color[:3],
    )


def rounded_rect_border_glow(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    width: float = 2.0,
    spread: float = 12.0,
    intensity: float = 0.65,
    color: RGBA = (0.45, 0.78, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel glowing border centered on the rounded rect edge.

    `width` controls the bright core thickness; `spread` controls how far
    the glow feathers inward and outward from the border.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    mi = _max_inner(p_min, p_max)
    hw = min(width * 0.5, mi)
    outer = max(spread, hw + 1.0)
    inner = min(outer, mi)
    return _PRESETS.get("border_glow", _t_border_glow).effect(
        *_pad(p_min, p_max, max(spread, width * 0.5 + 1.0) + 2.0),
        p_min=p_min, p_max=p_max, rounding=rounding,
        x0=-outer, x1=-hw, x3=hw, x4=inner,
        alpha_scale=intensity * color[3], rgb=color[:3],
    )


def neon_tube_border(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    width: float = 3.0,
    glow_width: float = 18.0,
    intensity: float = 0.8,
    color: RGBA = (0.25, 0.9, 1.0, 1.0),
    core_color: RGBA = (0.92, 1.0, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel neon tube border: bright core plus inner/outer glow.

    `width` is the bright tube thickness; `glow_width` is how far the
    colored aura feathers away from the core.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    mi = _max_inner(p_min, p_max)
    hw = min(width * 0.5, mi)
    glow = max(glow_width, hw + 1.0)
    inner = min(glow, mi)
    nodes = [-glow, -2.2 * hw, -hw, 0.0, hw, 2.2 * hw, inner]
    for i in range(1, len(nodes)):  # degenerate segments collapse to steps
        nodes[i] = max(nodes[i], nodes[i - 1])
    return _PRESETS.get("neon", _t_neon).effect(
        *_pad(p_min, p_max, max(glow_width, width * 0.5 + 1.0) + 2.0),
        p_min=p_min, p_max=p_max, rounding=rounding,
        x0=nodes[0], x1=nodes[1], x2=nodes[2], x4=nodes[4], x5=nodes[5], x6=nodes[6],
        rgb=color[:3], core_rgb=_rgba(core_color)[:3],
        alpha_scale=intensity * color[3],
    )


def rainbow_border(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    width: float = 3.0,
    intensity: float = 0.85,
) -> Effect:
    """
    A per-pixel border with colors cycling through the HSV spectrum.

    `progress` shifts the hue phase along the perimeter.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    return _PRESETS.get("rainbow", _t_rainbow).effect(
        *_pad(p_min, p_max, width * 0.5 + 2.0),
        p_min=p_min, p_max=p_max, rounding=rounding,
        hw=min(width * 0.5, _max_inner(p_min, p_max)),
        progress=progress, alpha_scale=intensity,
    )


def state_transition_glow(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    width: float = 20.0,
    intensity: float = 0.55,
    color: RGBA = (0.65, 0.95, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel full inner edge glow for short state transitions.

    `progress` is the transition decay: 0 is brightest, 1 is fully faded.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    p = _clamp01(progress)
    return _PRESETS.get("state_glow", _t_state_glow).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding,
        w=min(width * (0.75 + 0.35 * p), _max_inner(p_min, p_max)),
        alpha_scale=(1.0 - _s01(0.0, 1.0, p)) * intensity * color[3], rgb=color[:3],
    )


def magnetic_edge_glow(
    p_min: Point,
    p_max: Point,
    pointer: Point,
    rounding: float = 0.0,
    width: float = 18.0,
    reach: float = 120.0,
    intensity: float = 0.55,
    color: RGBA = (0.45, 0.85, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel inner edge glow oriented toward `pointer`.

    The brightest point is where the center-to-pointer ray meets the
    rounded boundary; brightness fades inward and along the edge over
    `reach` pixels.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    anchor = _boundary_anchor(p_min, p_max, rounding, _point(pointer))
    anchor_t, perimeter = _rect_path_params(p_min, p_max, rounding, anchor)
    return _PRESETS.get("magnetic", _t_magnetic).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding,
        w=min(width, _max_inner(p_min, p_max)),
        reach=max(reach, 1.0), anchor_t=anchor_t, perimeter=perimeter,
        alpha_scale=intensity * color[3], rgb=color[:3],
    )


def rounded_rect_glint(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    width: float = 5.0,
    length: float = 0.16,
    color: RGBA = (1.0, 0.9, 0.45, 1.0),
    softness: float = 1.0,
    inset: float = 1.5,
    corner_colors: tuple[RGBA, RGBA, RGBA, RGBA] | None = None,
) -> Effect:
    """
    A per-pixel glint traveling along the rounded rect border.

    `progress` is normalized to `[0, 1)` around the border path. `length`
    is the fraction of the perimeter covered. `corner_colors` is ordered
    tl, tr, br, bl.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    with_corners = corner_colors is not None
    values: dict = dict(
        p_min=p_min, p_max=p_max, rounding=rounding, inset=inset,
        hw=max(width * 0.5, 0.5), progress=progress % 1.0,
        half_len=max(length, 0.001) * 0.5, inv_softness=1.0 / max(softness, 0.05),
    )
    if with_corners:
        tl, tr, br, bl = corner_colors
        values.update(col_tl=_rgba(tl), col_tr=_rgba(tr), col_br=_rgba(br), col_bl=_rgba(bl))
    else:
        values.update(col=_rgba(color))
    return _PRESETS.get(("glint", with_corners), _t_glint, with_corners).effect(
        *_pad(p_min, p_max, width * 0.5 + 2.0), **values
    )


def corner_glints(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    width: float = 6.0,
    length: float = 0.58,
    intensity: float = 0.85,
    color: RGBA = (1.0, 0.86, 0.35, 1.0),
    softness: float = 1.0,
    inset: float = 2.0,
) -> Effect | None:
    """
    Per-pixel glints sweeping across the four rounded corners.

    `progress` moves the highlight through each corner arc from 0 to 1.
    `length` is the fraction of one corner arc covered by each glint.
    Returns None when the inset corner radius degenerates (nothing to draw).
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    w, h = p_max[0] - p_min[0], p_max[1] - p_min[1]
    r = max(0.0, min(rounding, min(w, h) * 0.5))
    rc = r - inset
    if rc <= 0.5:
        return None
    return _PRESETS.get("corner_glints", _t_corner_glints).effect(
        *_pad(p_min, p_max, width * 1.5 + 2.0),
        cx=(p_min[0] + p_max[0]) * 0.5, cy=(p_min[1] + p_max[1]) * 0.5,
        ccx0=p_min[0] + r, ccx1=p_max[0] - r, ccy0=p_min[1] + r, ccy1=p_max[1] - r,
        rc=rc, hw=min(max(width * 0.5, 0.5), rc - 0.25),
        sigma=max(length, 0.05) * 0.38 * max(softness, 0.2), progress=progress % 1.0,
        alpha_scale=intensity * color[3], rgb=color[:3],
    )


# -- radial family -----------------------------------------------------------------


def radial_gleam(
    p_min: Point,
    p_max: Point,
    center: Point,
    rounding: float = 0.0,
    radius: float = 80.0,
    intensity: float = 0.45,
    color: RGBA = (1.0, 1.0, 1.0, 1.0),
    aspect: float = 1.0,
) -> Effect:
    """
    A per-pixel radial highlight clipped to a rounded rect.

    `center` is in screen coordinates. `aspect` scales the vertical radius,
    so values below 1 create a flatter gleam.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    aspect = max(aspect, 0.05)
    return _PRESETS.get("gleam", _t_gleam).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding, center=_point(center),
        radii=(max(radius, 1.0), max(radius * aspect, 1.0)),
        alpha_scale=intensity * color[3], rgb=color[:3],
    )


def click_ripple(
    p_min: Point,
    p_max: Point,
    center: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    radius: float = 80.0,
    width: float = 24.0,
    intensity: float = 0.55,
    color: RGBA = (1.0, 1.0, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel touch ripple expanding from `center`, clipped to a rounded
    rect.

    `progress` is normalized from 0 to 1: a continuous expanding wash with a
    soft front, fading out toward the end of its lifetime.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    p = _clamp01(progress)
    fade = (1.0 - _s01(0.62, 1.0, p)) * _s01(0.0, 0.06, p)
    return _PRESETS.get("ripple", _t_ripple).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding, center=_point(center),
        ring_r=radius * (0.08 + p * 0.92), front=max(width, 1.0),
        alpha_scale=fade * intensity * color[3], rgb=color[:3],
    )


def shockwave(
    p_min: Point,
    p_max: Point,
    center: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    radius: float = 120.0,
    width: float = 18.0,
    intensity: float = 0.65,
    color: RGBA = (1.0, 1.0, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel hollow ring shockwave expanding from `center`, clipped to a
    rounded rect. Sharper and higher contrast than `click_ripple`.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    p = _clamp01(progress)
    fade = (1.0 - _s01(0.58, 1.0, p)) * _s01(0.0, 0.05, p)
    return _PRESETS.get("shockwave", _t_shockwave).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding, center=_point(center),
        ring_r=radius * p, hw=max(width * (0.85 + 0.35 * p) * 0.5, 1.0),
        alpha_scale=fade * intensity * color[3], rgb=color[:3],
    )


def press_flash(
    p_min: Point,
    p_max: Point,
    center: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    radius: float = 90.0,
    intensity: float = 0.55,
    color: RGBA = (1.0, 1.0, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel soft flash from `center`, clipped to rounded bounds.

    `progress` is normalized from 0 to 1 and represents the flash decay.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    color = _rgba(color)
    p = _clamp01(progress)
    return _PRESETS.get("flash", _t_flash).effect(
        p_min, p_max,
        p_min=p_min, p_max=p_max, rounding=rounding, center=_point(center),
        flash_r=max(radius * (0.35 + 0.65 * p), 1.0),
        alpha_scale=(1.0 - _s01(0.0, 1.0, p)) * intensity * color[3], rgb=color[:3],
    )


# -- textured -----------------------------------------------------------------------


def rounded_image_edge_fade(
    texture_id: int,
    p_min: Point,
    p_max: Point,
    uv_min: Point,
    uv_max: Point,
    rounding: float = 0.0,
    fade: float = 12.0,
    col: RGBA = (1.0, 1.0, 1.0, 1.0),
    min_alpha: float = 0.0,
) -> Effect:
    """
    An image whose alpha fades toward the rounded rect boundary.

    `min_alpha` controls the fade endpoint before clipping, so edge pixels
    can remain translucent instead of fading all the way to zero.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    col = _rgba(col)
    with_fade = fade > 0.0
    values: dict = dict(
        p_min=p_min, p_max=p_max, rounding=rounding,
        uv_min=_point(uv_min), uv_max=_point(uv_max),
        rgb=col[:3], col_a=col[3],
    )
    if with_fade:
        values.update(fade=fade, min_alpha=_clamp01(min_alpha))
    return _PRESETS.get(("edge_fade", with_fade), _t_edge_fade, with_fade).effect(
        p_min, p_max, int(texture_id), **values
    )


def rounded_image_linear_gradient(
    texture_id: int,
    p_min: Point,
    p_max: Point,
    uv_min: Point,
    uv_max: Point,
    angle_degrees: float,
    stops: Sequence[tuple[float, RGBA]],
    rounding: float = 0.0,
    flags: int = ROUND_CORNERS_ALL,
) -> Effect:
    """
    An image tinted by a linear gradient and clipped to a rounded rect.

    `angle_degrees` uses CSS linear-gradient angle semantics: 0 points up,
    90 points right, and positive angles rotate clockwise. `stops` is ordered
    as `(position, color)` pairs normalized across the image rectangle.
    `flags` selects which corners are rounded (`ROUND_CORNERS_*` constants).
    """
    p_min, p_max = _point(p_min), _point(p_max)
    w, h = p_max[0] - p_min[0], p_max[1] - p_min[1]
    stops = _normalize_gradient_stops(stops)
    angle = math.radians(angle_degrees)
    proj_min, proj_max = _gradient_proj_range(p_min, p_max, angle_degrees)

    values: dict = dict(
        p_min=p_min, p_max=p_max, rounding=rounding,
        uv_min=_point(uv_min), uv_max=_point(uv_max),
        dir=(math.sin(angle), math.cos(angle)),
        proj_min=proj_min, proj_range=max(proj_max - proj_min, 1.0),
        clip_softness=_mesh_clip_softness(w, h),
        c0=stops[0][1],
    )
    for i in range(1, len(stops)):
        values[f"pos{i - 1}"] = stops[i - 1][0]
        values[f"span{i}"] = max(stops[i][0] - stops[i - 1][0], 1e-5)
        values[f"c{i}"] = stops[i][1]

    key = ("linear_gradient", len(stops), int(flags))
    return _PRESETS.get(key, _t_linear_gradient, len(stops), int(flags)).effect(
        p_min, p_max, int(texture_id), **values
    )


# -- particles -----------------------------------------------------------------------


def path_particles(
    p_min: Point,
    p_max: Point,
    rounding: float = 0.0,
    progress: float = 0.0,
    count: int = 18,
    radius: float = 3.0,
    intensity: float = 0.75,
    trail: float = 0.35,
    inset: float = 0.0,
    color: RGBA = (0.65, 0.95, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel trail of soft particles flowing along a rounded rect.

    `progress` is normalized around the path. `trail` is the fraction of
    the perimeter covered by the tail, and `inset` moves the path inward.
    """
    p_min, p_max = _point(p_min), _point(p_max)
    return _PRESETS.get("particles_path", _t_particles_path).effect(
        *_pad(p_min, p_max, radius + 2.0),
        p_min=p_min, p_max=p_max, rounding=rounding, progress=progress,
        trail=trail, inset=inset, count=max(1, min(int(count), MAX_PARTICLES)),
        radius=radius, intensity=intensity, tint=_rgba(color),
    )


def spark_burst(
    center: Point,
    progress: float = 0.0,
    count: int = 22,
    radius: float = 3.0,
    spread: float = 72.0,
    intensity: float = 0.85,
    color: RGBA = (1.0, 0.78, 0.38, 1.0),
) -> Effect:
    """
    A per-pixel deterministic burst of spark streaks from `center`.

    `progress` is normalized from 0 to 1 and represents the burst lifetime.
    """
    center = _point(center)
    pad = spread * 1.3 + radius * 10.0 + 4.0
    return _PRESETS.get("particles_burst", _t_particles_burst).effect(
        (center[0] - pad, center[1] - pad), (center[0] + pad, center[1] + pad),
        center=center, progress=progress,
        count=max(1, min(int(count), MAX_PARTICLES)),
        radius=radius, spread=spread, intensity=intensity, tint=_rgba(color),
    )


def trail_dots(
    start: Point,
    end: Point,
    progress: float = 0.0,
    count: int = 18,
    radius: float = 4.0,
    spacing: float = 12.0,
    intensity: float = 0.75,
    color: RGBA = (0.55, 0.85, 1.0, 1.0),
) -> Effect:
    """
    A per-pixel trail of soft dots behind a moving point.

    `progress` moves the leading dot from `start` to `end`; `spacing` is
    the pixel distance between dots in the trail.
    """
    start, end = _point(start), _point(end)
    pad = radius + 2.0
    q_min = (min(start[0], end[0]) - pad, min(start[1], end[1]) - pad)
    q_max = (max(start[0], end[0]) + pad, max(start[1], end[1]) + pad)
    return _PRESETS.get("particles_trail", _t_particles_trail).effect(
        q_min, q_max,
        start=start, end=end, progress=progress,
        count=max(1, min(int(count), MAX_PARTICLES)),
        radius=radius, spacing=spacing, intensity=intensity, tint=_rgba(color),
    )
