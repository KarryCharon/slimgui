"""
Showcase: composed effects the old primitive+mode system could not express.

Every effect here is built purely from the `fragfx` vocabulary (fields x
profiles x noise x math) -- no new shaders, no new modes. Each card's
expression tree is a `Template` built once; animation only rebinds named
uniforms (zero recompiles).

Effects 1-15 are single composed templates; 16-18 choreograph existing
preset helpers to show multi-effect layering and timeline driving.
"""

from __future__ import annotations

import math
import time

from util import emit

from fragfx import FRAG, Template, TemplateParams, TemplateStore, Vec
from fragfx import color as fxc
from fragfx import effects as fxe
from fragfx import fields as fxf
from fragfx import math as fxm
from fragfx import noise as fxn
from fragfx import profiles as fxp
from slimgui import imgui


Point = tuple[float, float]

_ROUNDING = 16.0
_START_TIME = time.monotonic()
_TEMPLATES = TemplateStore()
_demo_texture: int | None = None


def set_demo_texture(texture_id: int | None) -> None:
    """Background texture for showcase cards that demo refraction effects."""
    global _demo_texture
    _demo_texture = None if texture_id is None else int(texture_id)


def _now() -> float:
    return time.monotonic() - _START_TIME


def _col(r: float, g: float, b: float, a: float) -> int:
    return imgui.color_convert_float4_to_u32((r, g, b, a))


def _s01(edge0: float, edge1: float, x: float) -> float:
    t = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def _card(draw_list: imgui.DrawList, p_min: Point, p_max: Point, bg: tuple[float, float, float]) -> None:
    draw_list.add_rect_filled(p_min, p_max, _col(*bg, 1.0), _ROUNDING)


def _frame(draw_list: imgui.DrawList, p_min: Point, p_max: Point, alpha: float = 0.25) -> None:
    draw_list.add_rect(p_min, p_max, _col(1.0, 1.0, 1.0, alpha), _ROUNDING, thickness=1.2)


def _pad(p_min: Point, p_max: Point, pad: float) -> tuple[Point, Point]:
    return (p_min[0] - pad, p_min[1] - pad), (p_max[0] + pad, p_max[1] + pad)


def _rect_params(p: TemplateParams) -> fxf.RoundedRect:
    return fxf.RoundedRect(p.vec2("p_min"), p.vec2("p_max"), p.f("rounding"))


def _local_frag(p: TemplateParams):
    """卡片局部坐标(FRAG - p_min):噪声场随卡片移动,而不是钉在屏幕上。
    复用已声明的 p_min 参数节点(CSE 不增加 uniform 槽位)。"""
    return FRAG - p.named["p_min"]


# -- 1. dissolve_burn: fbm 阈值溶解 + 燃烧边缘 ------------------------------------


def _t_dissolve() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    n = fxn.fbm(_local_frag(p) * p.f("scale") + p.vec2("offset"), 4)
    d = n - p.f("threshold")  # > 0: still solid
    body = fxm.smooth01(0.0, 0.08, d)
    rim = fxp.gauss(d / 0.05)
    rim_col = fxm.mix(p.vec3("ember_rgb"), p.vec3("flame_rgb"), fxp.gauss(d / 0.025))
    col = fxm.mix(p.vec3("base_rgb"), rim_col, fxm.clamp(rim * 1.6, 0.0, 1.0))
    alpha = fxm.clamp(body * p.f("body_alpha") + rim, 0.0, 1.0) * rect.clip()
    return Template(fxc.rgba(col, alpha), p)


def draw_dissolve_burn(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.05, 0.05, 0.08))
    cycle = (t / 3.2) % 1.0
    threshold = (0.5 - abs(cycle - 0.5)) * 2.0 * 1.25 - 0.1  # sweep in, sweep out
    emit(
        draw_list,
        _TEMPLATES.get("dissolve", _t_dissolve).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            scale=0.045,
            offset=(t * 1.5, 0.0),
            threshold=threshold,
            base_rgb=(0.75, 0.78, 0.85),
            body_alpha=0.85,
            ember_rgb=(1.0, 0.28, 0.04),
            flame_rgb=(1.0, 0.85, 0.35),
        ),
    )
    _frame(draw_list, p_min, p_max)


# -- 2. flame_border: 内边火焰 (edge_profile x 上升 fbm) ----------------------------


def _t_flame() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    u_n = fxm.clamp(-rect.sdf / p.f("w"), 0.0, 1.0)  # 0 at the edge -> 1 inward
    n = fxn.fbm(_local_frag(p) * p.f("scale") + p.vec2("offset"), 4)
    heat = (1.0 - u_n) * (0.45 + 0.75 * n)
    flame = fxm.smooth01(0.42, 0.78, heat)
    col = fxm.mix(p.vec3("deep_rgb"), p.vec3("hot_rgb"), fxm.smooth01(0.6, 1.0, heat))
    alpha = flame * fxm.step(0.0, -rect.sdf) * p.f("intensity")
    return Template(fxc.rgba(col, alpha), p)


def draw_flame_border(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.08, 0.04, 0.03))
    emit(
        draw_list,
        _TEMPLATES.get("flame", _t_flame).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            w=26.0,
            scale=0.09,
            offset=(0.0, t * 4.0),
            deep_rgb=(0.9, 0.16, 0.02),
            hot_rgb=(1.0, 0.92, 0.45),
            intensity=0.95,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.2)


# -- 3. aurora_card: fbm 光幕 x HSV 漂移 ----------------------------------------------


def _t_aurora() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    k = rect.uv()
    n = fxn.fbm(k * p.vec2("nscale") + p.vec2("noffset"), 4)
    curtain = fxp.gauss((k.y - (0.42 + (n - 0.5) * p.f("wave"))) / p.f("width"))
    col = fxc.hsv2rgb(fxm.fract(p.f("hue") + n * 0.25), 0.65, 1.0)
    alpha = curtain * (0.35 + 0.65 * n) * p.f("intensity") * rect.clip()
    return Template(fxc.rgba(col, alpha), p)


def draw_aurora_card(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.03, 0.04, 0.10))
    emit(
        draw_list,
        _TEMPLATES.get("aurora", _t_aurora).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            nscale=(2.6, 1.4),
            noffset=(t * 0.22, t * 0.07),
            wave=0.55,
            width=0.24,
            hue=0.38 + 0.06 * math.sin(t * 0.5),
            intensity=0.8,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.18)


# -- 4. electric_border: simplex 抖动的电弧边框 -----------------------------------------


def _t_electric() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    d = rect.sdf + p.f("inset") + fxn.simplex(_local_frag(p) * p.f("scale") + p.vec2("offset")) * p.f("amp")
    core = fxp.gauss(d / p.f("core_w"))
    halo = fxp.gauss(d / p.f("halo_w")) * 0.45
    col = fxm.mix(p.vec3("glow_rgb"), (1.0, 1.0, 1.0), core)
    return Template(fxc.rgba(col, (core + halo) * p.f("intensity")), p)


def draw_electric_border(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.05, 0.06, 0.10))
    amp, halo_w = 4.5, 7.0
    emit(
        draw_list,
        _TEMPLATES.get("electric", _t_electric).effect(
            *_pad(p_min, p_max, amp + halo_w + 2.0),
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            inset=3.0,
            scale=0.11,
            offset=(t * 7.0, t * 6.1),
            amp=amp,
            core_w=1.1,
            halo_w=halo_w,
            glow_rgb=(0.3, 0.7, 1.0),
            intensity=0.95,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.15)


# -- 5. energy_shield: 边缘 fresnel x 冲击波前 x 噪声闪烁 ----------------------------------


def _t_shield() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    fres = fxp.edge_profile(-rect.sdf, p.f("w"), 0.85, 0.4, 0.12)
    wave = fxp.gauss((fxm.length(FRAG - p.vec2("center")) - p.f("wave_r")) / p.f("wave_w")) * p.f("wave_a")
    flicker = 0.7 + 0.3 * fxn.noise(_local_frag(p) * 0.07 + p.vec2("foffset"))
    col = fxm.mix(p.vec3("rgb"), (1.0, 1.0, 1.0), wave)
    alpha = (fres * 0.8 + wave) * flicker * rect.clip() * p.f("intensity")
    return Template(fxc.rgba(col, alpha), p)


def draw_energy_shield(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.02, 0.06, 0.08))
    cycle = (t / 1.8) % 1.0
    center = (p_min[0] + size[0] * 0.5, p_min[1] + size[1] * 0.5)
    emit(
        draw_list,
        _TEMPLATES.get("shield", _t_shield).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            w=16.0,
            center=center,
            wave_r=cycle * size[0] * 0.62,
            wave_w=22.0,
            wave_a=(1.0 - cycle) * 0.9,
            foffset=(t * 6.0, 0.0),
            rgb=(0.25, 0.95, 0.85),
            intensity=0.85,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.2)


# -- 6. glitch_sweep: 量化行噪声 x 扫描带 ------------------------------------------------


def _t_glitch() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    k = rect.uv()
    rows = p.f("rows")
    seed = p.f("seed")
    row = fxm.floor(k.y * rows) / rows
    rnd = fxn.noise(Vec(row * 37.0, seed))
    rnd2 = fxn.noise(Vec(row * 53.0 + 11.0, seed))
    band = fxp.gauss((k.x - p.f("sweep")) / p.f("band_w"))
    on = fxm.step(0.45, rnd)
    col = fxm.mix(p.vec3("rgb_a"), p.vec3("rgb_b"), rnd2)
    alpha = on * band * (0.4 + 0.6 * rnd2) * p.f("intensity") * rect.clip()
    return Template(fxc.rgba(col, alpha), p)


def draw_glitch_sweep(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.07, 0.07, 0.09))
    emit(
        draw_list,
        _TEMPLATES.get("glitch", _t_glitch).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            rows=9.0,
            seed=math.floor(t * 9.0) * 1.37,  # stepwise reshuffle
            sweep=(t / 1.4) % 1.0,
            band_w=0.16,
            rgb_a=(1.0, 0.25, 0.45),
            rgb_b=(0.25, 0.95, 1.0),
            intensity=0.95,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.2)


# -- 7. vortex_gleam: 旋臂流光 (atan2 + 半径扭曲) ------------------------------------------


def _t_vortex() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    rel = FRAG - p.vec2("center")
    r = fxm.length(rel)
    arm = fxm.pow(0.5 + 0.5 * fxm.sin(fxm.atan2(rel.y, rel.x) * p.f("arms") + r * p.f("twist") - p.f("phase")), p.f("sharp"))
    rn = fxm.clamp(r / p.f("radius"), 0.0, 1.0)
    col = fxm.mix((1.0, 1.0, 1.0), p.vec3("rgb"), rn)
    alpha = arm * fxp.smoothfall(rn) * p.f("intensity") * rect.clip()
    return Template(fxc.rgba(col, alpha), p)


def draw_vortex_gleam(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.06, 0.04, 0.10))
    center = (p_min[0] + size[0] * 0.5, p_min[1] + size[1] * 0.5)
    emit(
        draw_list,
        _TEMPLATES.get("vortex", _t_vortex).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            center=center,
            arms=3.0,
            twist=0.16,
            phase=t * 2.2,
            sharp=2.4,
            radius=size[0] * 0.42,
            rgb=(0.55, 0.35, 1.0),
            intensity=0.8,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.2)


# -- 8. flame_border_dual: 内外同时火焰 (|sdf| 双侧热场, 内焰/外焰双色) ----------------------


def _t_flame_dual() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    inside = fxm.step(0.0, -rect.sdf)  # 1 inside, 0 outside
    u_n = fxm.clamp(fxm.abs(rect.sdf) / p.f("w"), 0.0, 1.0)  # 0 at the edge -> 1 away (both sides)
    q = _local_frag(p) * p.f("scale")
    n_in = fxn.fbm(q + p.vec2("offset_in"), 4)
    n_out = fxn.fbm(q + p.vec2("offset_out"), 4)
    n = fxm.mix(n_out, n_in, inside)
    heat = (1.0 - u_n) * (0.45 + 0.75 * n)
    flame = fxm.smooth01(0.42, 0.78, heat)
    tip = fxm.smooth01(0.6, 1.0, heat)
    col_in = fxm.mix(p.vec3("deep_in"), p.vec3("hot_in"), tip)
    col_out = fxm.mix(p.vec3("deep_out"), p.vec3("hot_out"), tip)
    col = fxm.mix(col_out, col_in, inside)
    return Template(fxc.rgba(col, flame * p.f("intensity")), p)


def draw_flame_border_dual(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    w = 24.0
    _card(draw_list, p_min, p_max, (0.06, 0.04, 0.05))
    emit(
        draw_list,
        _TEMPLATES.get("flame_dual", _t_flame_dual).effect(
            *_pad(p_min, p_max, w + 2.0),
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            w=w,
            scale=0.09,
            offset_in=(0.0, t * 4.0),
            offset_out=(31.7, t * 5.2),
            deep_in=(0.9, 0.16, 0.02),
            hot_in=(1.0, 0.92, 0.45),
            deep_out=(0.05, 0.22, 0.9),
            hot_out=(0.55, 0.92, 1.0),
            intensity=0.95,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.2)


# -- 9. laser_frame: 脉冲激光柱外框 (噪波束宽 x 顺时针流动脉冲) -------------------------------


def _t_laser_frame() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    pt = rect.path_t  # increases clockwise around the perimeter
    n = fxn.fbm(Vec(pt * p.f("nfreq"), p.f("ntime")), 3)  # beam-width jitter along the path
    d = fxm.abs(rect.sdf + p.f("inset"))
    core = fxp.gauss(d / (p.f("core_w") * (0.55 + 0.9 * n)))
    halo = fxp.gauss(d / p.f("halo_w")) * 0.5
    # comet pulses: heads advance clockwise as phase grows, tails trail behind
    pulse = fxm.pow(fxm.fract(pt * p.f("heads") - p.f("phase")), p.f("sharp"))
    base = p.f("base")
    energy = base + (1.0 - base) * pulse
    col = fxm.mix(p.vec3("rgb"), (1.0, 1.0, 1.0), core * pulse)
    alpha = (core + halo) * energy * (0.6 + 0.6 * n) * p.f("intensity")
    return Template(fxc.rgba(col, alpha), p)


def draw_laser_frame(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    halo_w = 9.0
    _card(draw_list, p_min, p_max, (0.04, 0.05, 0.09))
    emit(
        draw_list,
        _TEMPLATES.get("laser_frame", _t_laser_frame).effect(
            *_pad(p_min, p_max, halo_w + 4.0),
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            inset=2.0,
            nfreq=26.0,
            ntime=t * 2.4,
            core_w=2.2,
            halo_w=halo_w,
            heads=3.0,
            phase=t * 1.1,
            sharp=6.0,
            base=0.22,
            rgb=(1.0, 0.25, 0.35),
            intensity=1.0,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.15)


# -- 10. lava_cracks: 熔岩裂纹 (域扭曲 fbm x 脊线发光) ----------------------------------------


def _t_lava() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    q = _local_frag(p) * p.f("scale")
    warp = Vec(fxn.fbm(q + p.vec2("off_a"), 4), fxn.fbm(q + p.vec2("off_b"), 4))
    n = fxn.fbm(q + warp * p.f("warp"), 4)
    ridge = 1.0 - fxm.abs(n * 2.0 - 1.0)  # ridged noise: bright filaments
    crack = fxm.pow(fxm.clamp(ridge, 0.0, 1.0), p.f("sharp"))
    glow = fxm.smooth01(0.55, 1.0, crack) * p.f("pulse")
    col = fxm.mix(p.vec3("rock_rgb"), p.vec3("lava_rgb"), crack)
    col = fxm.mix(col, p.vec3("hot_rgb"), glow)
    alpha = (0.7 + 0.3 * crack) * rect.clip() * p.f("intensity")
    return Template(fxc.rgba(col, alpha), p)


def draw_lava_cracks(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.05, 0.03, 0.03))
    emit(
        draw_list,
        _TEMPLATES.get("lava", _t_lava).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            scale=0.03,
            warp=1.6,
            off_a=(t * 0.12, t * 0.05),
            off_b=(5.2 - t * 0.08, 1.3 + t * 0.1),
            sharp=3.2,
            pulse=0.7 + 0.3 * math.sin(t * 2.1),
            rock_rgb=(0.1, 0.06, 0.07),
            lava_rgb=(1.0, 0.32, 0.05),
            hot_rgb=(1.0, 0.9, 0.5),
            intensity=0.95,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.2)


# -- 11. hologram: 全息投影 (扫描线 x 亮带扫掠 x fresnel 边缘 x 闪烁) --------------------------


def _t_hologram() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    k = rect.uv()
    scan = 0.78 + 0.22 * fxm.sin(k.y * p.f("lines") + p.f("phase"))
    band = fxp.gauss((k.y - p.f("sweep")) / 0.07) * 0.65
    fres = fxp.edge_profile(-rect.sdf, p.f("w"), 0.9, 0.5, 0.2)
    seed = p.f("seed")
    rowjit = 0.75 + 0.25 * fxn.noise(Vec(k.y * 60.0, seed))  # broken-signal rows
    flick = 0.82 + 0.18 * fxn.noise(Vec(seed * 1.7, 3.3))
    body = (0.3 + band) * scan * rowjit
    col = fxm.mix(p.vec3("rgb"), (1.0, 1.0, 1.0), band)
    alpha = (body * rect.clip() + fres * 0.9) * flick * p.f("intensity")
    return Template(fxc.rgba(col, alpha), p)


def draw_hologram(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.02, 0.05, 0.07))
    emit(
        draw_list,
        _TEMPLATES.get("hologram", _t_hologram).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            lines=90.0,
            phase=t * 5.0,
            sweep=(t / 2.6) % 1.3 - 0.15,
            w=14.0,
            seed=math.floor(t * 16.0) * 0.731,
            rgb=(0.3, 0.95, 0.95),
            intensity=0.8,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.18)


# -- 12. wave_interference: 水波干涉 (双波源 sin 场叠加 x 距离衰减) ----------------------------


def _t_interference() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    d1 = fxm.length(FRAG - p.vec2("c1"))
    d2 = fxm.length(FRAG - p.vec2("c2"))
    freq, phase = p.f("freq"), p.f("phase")
    s = (fxm.sin(d1 * freq - phase) + fxm.sin(d2 * freq - phase)) * 0.5
    crest = fxm.pow(fxm.clamp(fxm.abs(s), 0.0, 1.0), p.f("sharp"))
    att = fxp.smoothfall(fxm.clamp(fxm.min(d1, d2) / p.f("radius"), 0.0, 1.0))
    col = fxm.mix(p.vec3("deep_rgb"), p.vec3("crest_rgb"), crest)
    alpha = (0.18 + 0.82 * crest) * att * rect.clip() * p.f("intensity")
    return Template(fxc.rgba(col, alpha), p)


def draw_wave_interference(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.02, 0.05, 0.09))
    cx, cy = p_min[0] + size[0] * 0.5, p_min[1] + size[1] * 0.5
    orbit = size[0] * 0.22
    a = t * 0.7
    emit(
        draw_list,
        _TEMPLATES.get("interference", _t_interference).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            c1=(cx + orbit * math.cos(a), cy + orbit * 0.6 * math.sin(a)),
            c2=(cx - orbit * math.cos(a * 0.8), cy - orbit * 0.6 * math.sin(a * 0.8)),
            freq=0.55,
            phase=t * 4.0,
            sharp=2.6,
            radius=size[0] * 0.85,
            deep_rgb=(0.05, 0.25, 0.5),
            crest_rgb=(0.6, 0.95, 1.0),
            intensity=0.9,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.18)


# -- 13. matrix_rain: 数字雨 (列速率噪声 x 下落头部 x 字符格闪烁) ------------------------------


def _t_matrix() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    k = rect.uv()
    col_i = fxm.floor(k.x * p.f("cols"))
    speed = 0.4 + 0.6 * fxn.noise(Vec(col_i * 7.31, 1.7))
    head = fxm.fract(p.f("time") * speed + fxn.noise(Vec(col_i * 3.7, 9.1)) * 7.0)
    dy = fxm.fract(head - k.y)  # 0 at the falling head, grows along the trail above
    trail = fxm.pow(1.0 - dy, p.f("tail"))
    cell = fxn.noise(Vec(col_i * 13.7 + 31.0, fxm.floor(k.y * p.f("rows")) * 17.3 + p.f("reseed")))
    glyph = fxm.step(0.25, cell) * (0.35 + 0.65 * cell)  # flickering "characters"
    head_glow = fxp.gauss(dy / 0.04)
    col = fxm.mix(p.vec3("rgb"), (0.85, 1.0, 0.9), head_glow)
    alpha = trail * glyph * rect.clip() * p.f("intensity")
    return Template(fxc.rgba(col, alpha), p)


def draw_matrix_rain(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.01, 0.04, 0.02))
    emit(
        draw_list,
        _TEMPLATES.get("matrix", _t_matrix).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=_ROUNDING,
            cols=26.0,
            rows=14.0,
            time=t * 0.5,
            tail=3.4,
            reseed=math.floor(t * 10.0) * 1.13,
            rgb=(0.2, 0.95, 0.4),
            intensity=0.95,
        ),
    )
    _frame(draw_list, p_min, p_max, 0.18)


# -- 14. water_ripple: 拟真点击水波 (噪波波前 x 色散波包 x 明暗折射着色) ------------------------


def _t_water() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    d = fxm.length(FRAG - p.vec2("center"))
    # organic front: the radial distance itself is perturbed by positional fbm,
    # so every crest is an irregular closed curve instead of a perfect circle
    dd = d + (fxn.fbm(_local_frag(p) * p.f("nscale") + p.vec2("nseed"), 3) - 0.5) * p.f("wobble")
    att = fxp.smoothfall(fxm.clamp(dd / p.f("att_r"), 0.0, 1.0))  # energy spreads over the ring
    # main packet: several internal crests under a gaussian envelope (sin x gauss)
    ring1 = fxm.sin(dd * p.f("k") - p.f("phase")) * fxp.gauss((dd - p.f("front")) / p.f("packet_w")) * p.f("amp")
    # slower rebound packet trailing behind the main front
    ring2 = fxm.sin(dd * p.f("k2") - p.f("phase2")) * fxp.gauss((dd - p.f("front2")) / p.f("packet2_w")) * p.f("amp2")
    s = fxm.clamp((ring1 + ring2) * att, -1.0, 1.0)  # signed surface height
    spec = fxm.pow(fxm.clamp(s, 0.0, 1.0), 4.0)  # specular sparkle on crest tips
    splash = fxp.gauss(d / p.f("splash_r")) * p.f("splash_a")  # initial plop
    col = fxm.mix(fxm.mix(p.vec3("trough_rgb"), p.vec3("crest_rgb"), s * 0.5 + 0.5), (1.0, 1.0, 1.0), spec * 0.85)
    alpha = (fxm.abs(s) * 0.85 + spec * 0.35 + splash) * p.f("fade") * rect.clip()
    return Template(fxc.rgba(col, alpha), p)


def water_ripple(
    draw_list: imgui.DrawList,
    p_min: Point,
    p_max: Point,
    center: Point,
    progress: float,
    seed: float = 0.0,
    rounding: float = _ROUNDING,
    radius: float | None = None,
    color: tuple[float, float, float] = (0.55, 0.85, 1.0),
    intensity: float = 1.0,
) -> None:
    """Realistic click ripple: `progress` 0 -> 1 drives the whole lifetime.

    `seed` reshuffles the front-distortion noise (pick a new one per click).
    Physically-inspired knobs are derived from `progress`: the front
    decelerates, the wavelength stretches (dispersion), the packet widens,
    and a slower rebound ring trails behind.
    """
    p = min(max(progress, 0.0), 1.0)
    if p >= 1.0:
        return
    if radius is None:
        radius = math.hypot(p_max[0] - p_min[0], p_max[1] - p_min[1]) * 0.55
    front = radius * math.pow(p, 0.8)
    wl = 26.0 + 70.0 * p  # dispersion: wavelength grows over time
    k = math.tau / wl
    p2 = max(p - 0.22, 0.0) / 0.78
    front2 = radius * 0.75 * math.pow(p2, 0.8)
    k2 = math.tau / (18.0 + 40.0 * p2)
    fade = (1.0 - _s01(0.6, 1.0, p)) * _s01(0.0, 0.02, p) * intensity
    emit(
        draw_list,
        _TEMPLATES.get("water", _t_water).effect(
            p_min,
            p_max,
            p_min=p_min,
            p_max=p_max,
            rounding=rounding,
            center=center,
            nscale=0.05,
            nseed=(seed * 37.7 % 19.0, seed * 61.3 % 23.0),
            wobble=2.5 + 9.0 * p,
            att_r=radius * 1.35,
            # phase advances faster than the front: crests drift forward through
            # the envelope, like real capillary waves (phase velocity > group)
            k=k,
            phase=front * k * 1.35,
            front=front,
            packet_w=14.0 + 60.0 * p,
            amp=1.0,
            k2=k2,
            phase2=front2 * k2 * 1.35,
            front2=front2,
            packet2_w=10.0 + 34.0 * p2,
            amp2=0.55 * _s01(0.0, 0.25, p2),
            splash_r=7.0 + 90.0 * p,
            splash_a=(1.0 - p) ** 4 * 1.2,
            trough_rgb=tuple(c * 0.16 for c in color),
            crest_rgb=color,
            fade=fade,
        ),
    )


def draw_water_ripple(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    _card(draw_list, p_min, p_max, (0.03, 0.08, 0.12))
    cycle = t / 2.4
    water_ripple(
        draw_list,
        p_min,
        p_max,
        ((p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5),
        cycle % 1.0,
        seed=math.floor(cycle) * 1.37 + 3.1,
    )
    _frame(draw_list, p_min, p_max, 0.18)


# -- 15. water_refract: 折射水波 (解析梯度 -> UV 位移采样 x 法线光照 x 高光) --------------------
# Shadertoy 参考的核心是对背景纹理做位移采样 + 法线光照; 这里高度场是解析的
# (sin x gauss 波包), 所以梯度也解析可得 (cos x gauss), 无需邻域采样。

_LIGHT = (0.227, -0.566, 0.793)  # normalize(vec3(.2, -.5, .7)), y down in screen space


def _t_water_tex() -> Template:
    p = TemplateParams()
    rect = _rect_params(p)
    rel = FRAG - p.vec2("center")
    d = fxm.length(rel)
    dir_ = rel / fxm.max(d, 1.0)  # radial unit vector: the wave's slope direction
    dd = d + (fxn.fbm(_local_frag(p) * p.f("nscale") + p.vec2("nseed"), 3) - 0.5) * p.f("wobble")
    att = fxp.smoothfall(fxm.clamp(dd / p.f("att_r"), 0.0, 1.0))
    env1 = fxp.gauss((dd - p.f("front")) / p.f("packet_w"))
    env2 = fxp.gauss((dd - p.f("front2")) / p.f("packet2_w"))
    ph1 = dd * p.f("k") - p.f("phase")
    ph2 = dd * p.f("k2") - p.f("phase2")
    amp1, amp2 = p.f("amp"), p.f("amp2")
    g = (fxm.cos(ph1) * env1 * amp1 + fxm.cos(ph2) * env2 * amp2) * att  # radial slope dh/dr
    h = (fxm.sin(ph1) * env1 * amp1 + fxm.sin(ph2) * env2 * amp2) * att  # surface height

    # refraction: shift the sampled texel along the radial slope
    uv = fxm.mix(p.vec2("uv_min"), p.vec2("uv_max"), rect.uv())
    sample = fxc.tex(uv + dir_ * (g * p.f("refr")) * p.vec2("px2uv"))

    # lighting against the analytic normal n = (-g * dir, 1) / sqrt(1 + g^2)
    lx, ly, lz = _LIGHT
    inv_n = fxm.pow(1.0 + g * g, -0.5)
    ndotl = (lz - g * fxm.dot(dir_, Vec(lx, ly))) * inv_n
    lighting = fxm.clamp(ndotl * (1.0 / lz), 0.0, 1.6)  # flat surface -> exactly 1.0
    spec = fxm.pow(fxm.clamp(2.0 * ndotl * inv_n - lz, 0.0, 1.0), 32.0)  # -reflect(l, n).z

    tint = fxm.clamp(fxm.abs(h) * 3.0, 0.0, 1.0) * 0.22  # watery cast inside the packet
    splash = fxp.gauss(d / p.f("splash_r")) * p.f("splash_a")
    col = fxm.mix(sample.rgb, (0.7, 0.8, 1.0), tint) * lighting + (spec + splash)
    return Template(fxc.rgba(col, sample.a * rect.clip()), p)


def water_ripple_refract(
    draw_list: imgui.DrawList,
    texture_id: int,
    p_min: Point,
    p_max: Point,
    center: Point,
    progress: float,
    seed: float = 0.0,
    rounding: float = _ROUNDING,
    uv_min: Point = (0.0, 0.0),
    uv_max: Point = (1.0, 1.0),
    radius: float | None = None,
    intensity: float = 1.0,
) -> None:
    """Refractive click ripple over a textured rect (the effect draws the
    image itself; with no active wave it renders the plain image).

    Same physically-inspired progress mapping as `water_ripple`, but the
    wave is rendered by *displacing the texture lookup* along the analytic
    surface slope plus diffuse/specular lighting -- not by painting rings.
    """
    p = min(max(progress, 0.0), 1.0)
    w, h = p_max[0] - p_min[0], p_max[1] - p_min[1]
    if radius is None:
        radius = math.hypot(w, h) * 0.55
    front = radius * math.pow(p, 0.8)
    k = math.tau / (26.0 + 70.0 * p)  # dispersion: wavelength grows over time
    p2 = max(p - 0.22, 0.0) / 0.78
    front2 = radius * 0.75 * math.pow(p2, 0.8)
    k2 = math.tau / (18.0 + 40.0 * p2)
    decay = (1.0 - _s01(0.55, 1.0, p)) * _s01(0.0, 0.02, p) * intensity
    height = 3.0 * decay  # surface amplitude in px; slope amp = height * k
    emit(
        draw_list,
        _TEMPLATES.get("water_tex", _t_water_tex).effect(
            p_min,
            p_max,
            int(texture_id),
            p_min=p_min,
            p_max=p_max,
            rounding=rounding,
            center=center,
            uv_min=uv_min,
            uv_max=uv_max,
            px2uv=((uv_max[0] - uv_min[0]) / w, (uv_max[1] - uv_min[1]) / h),
            nscale=0.05,
            nseed=(seed * 37.7 % 19.0, seed * 61.3 % 23.0),
            wobble=2.5 + 9.0 * p,
            att_r=radius * 1.35,
            k=k,
            phase=front * k * 1.35,
            front=front,
            packet_w=14.0 + 60.0 * p,
            amp=height * k,
            k2=k2,
            phase2=front2 * k2 * 1.35,
            front2=front2,
            packet2_w=10.0 + 34.0 * p2,
            amp2=height * 0.6 * k2 * _s01(0.0, 0.25, p2),
            refr=10.0,
            splash_r=7.0 + 90.0 * p,
            splash_a=(1.0 - p) ** 4 * 0.9 * intensity,
        ),
    )


def draw_water_refract(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    cycle = t / 2.6
    center = ((p_min[0] + p_max[0]) * 0.5, (p_min[1] + p_max[1]) * 0.5)
    seed = math.floor(cycle) * 1.37 + 3.1
    if _demo_texture is None:  # no texture registered: procedural fallback
        _card(draw_list, p_min, p_max, (0.03, 0.08, 0.12))
        water_ripple(draw_list, p_min, p_max, center, cycle % 1.0, seed=seed)
    else:
        water_ripple_refract(
            draw_list,
            _demo_texture,
            p_min,
            p_max,
            center,
            cycle % 1.0,
            seed=seed,
            uv_max=(size[0] / 96.0, size[1] / 96.0),  # checker at native tile scale
        )
    _frame(draw_list, p_min, p_max, 0.18)


# -- 16. neon_pulse_stack: 三层预设同相位呼吸 -----------------------------------------------


def draw_neon_pulse_stack(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    breath = 0.5 + 0.5 * math.sin(t * math.tau / 2.4)
    _card(draw_list, p_min, p_max, (0.05, 0.05, 0.09))
    emit(draw_list, fxe.soft_glow_rect(p_min, p_max, rounding=_ROUNDING, spread=12.0 + 9.0 * breath, intensity=0.3 + 0.3 * breath, color=(0.25, 0.9, 1.0, 1.0)))
    emit(draw_list, fxe.neon_tube_border(p_min, p_max, rounding=_ROUNDING, width=3.0, glow_width=14.0, intensity=0.55 + 0.35 * breath, color=(0.25, 0.9, 1.0, 1.0)))
    emit(draw_list, fxe.corner_glints(p_min, p_max, rounding=_ROUNDING, progress=(t / 3.0) % 1.0, width=6.0, intensity=0.6 + 0.3 * breath, color=(0.8, 1.0, 1.0, 1.0)))


# -- 17. card_entrance: 时间轴编排的一次性入场反馈 -----------------------------------------------


def draw_card_entrance(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    cycle = t % 2.6
    center = (p_min[0] + size[0] * 0.5, p_min[1] + size[1] * 0.5)
    _card(draw_list, p_min, p_max, (0.07, 0.09, 0.13))
    if cycle < 1.2:
        emit(draw_list, fxe.state_transition_glow(p_min, p_max, rounding=_ROUNDING, progress=cycle / 1.2, width=22.0, intensity=0.7, color=(0.6, 0.95, 1.0, 1.0)))
    if cycle < 0.9:
        emit(draw_list, fxe.shockwave(p_min, p_max, center, rounding=_ROUNDING, progress=cycle / 0.9, radius=size[0] * 0.55, width=16.0, intensity=0.7))
    if 0.08 < cycle < 1.0:
        emit(draw_list, fxe.spark_burst(center, progress=(cycle - 0.08) / 0.92, count=22, radius=2.6, spread=size[0] * 0.32, intensity=0.85))
    _frame(draw_list, p_min, p_max, 0.25)


# -- 18. loading_orbit: 粒子环绕 + 反向 glint + 中心脉动 -----------------------------------------


def draw_loading_orbit(draw_list: imgui.DrawList, pos: Point, size: Point, t: float | None = None) -> None:
    t = _now() if t is None else t
    p_min, p_max = pos, (pos[0] + size[0], pos[1] + size[1])
    pulse = 0.5 + 0.5 * math.sin(t * math.tau / 1.6)
    center = (p_min[0] + size[0] * 0.5, p_min[1] + size[1] * 0.5)
    _card(draw_list, p_min, p_max, (0.05, 0.07, 0.11))
    emit(draw_list, fxe.radial_gleam(p_min, p_max, center, rounding=_ROUNDING, radius=size[0] * 0.2, intensity=0.25 + 0.3 * pulse, color=(0.6, 0.85, 1.0, 1.0), aspect=0.5))
    emit(draw_list, fxe.path_particles(p_min, p_max, rounding=_ROUNDING, progress=(t / 2.2) % 1.0, count=20, radius=3.2, trail=0.42, inset=6.0, color=(0.55, 0.9, 1.0, 1.0)))
    emit(draw_list, fxe.rounded_rect_glint(p_min, p_max, rounding=_ROUNDING, progress=(-t / 2.2) % 1.0, width=4.0, length=0.2, inset=1.5, color=(1.0, 0.85, 0.45, 1.0)))
    _frame(draw_list, p_min, p_max, 0.2)


# -- gallery wiring ----------------------------------------------------------------------------

# (title, description, draw(draw_list, pos, size))
SHOWCASE_DEMOS = [
    ("dissolve_burn", "fbm 阈值溶解 + 燃烧边缘。", draw_dissolve_burn),
    ("flame_border", "内边火焰: edge profile x 上升 fbm。", draw_flame_border),
    ("aurora_card", "极光光幕: fbm x HSV 漂移。", draw_aurora_card),
    ("electric_border", "电弧边框: simplex 抖动 SDF。", draw_electric_border),
    ("energy_shield", "能量护盾: fresnel x 波前 x 闪烁。", draw_energy_shield),
    ("glitch_sweep", "故障扫描: 量化行噪声 x 扫描带。", draw_glitch_sweep),
    ("vortex_gleam", "旋涡流光: atan2 旋臂 + 半径扭曲。", draw_vortex_gleam),
    ("flame_border_dual", "内外双焰: |sdf| 双侧热场, 内橙外蓝。", draw_flame_border_dual),
    ("laser_frame", "脉冲激光外框: 噪波束宽 x 顺时针流动。", draw_laser_frame),
    ("lava_cracks", "熔岩裂纹: 域扭曲 fbm x 脊线发光。", draw_lava_cracks),
    ("hologram", "全息投影: 扫描线 x 扫掠 x 信号闪烁。", draw_hologram),
    ("wave_interference", "水波干涉: 双波源叠加 x 距离衰减。", draw_wave_interference),
    ("matrix_rain", "数字雨: 列速率噪声 x 字符格闪烁。", draw_matrix_rain),
    ("water_ripple", "拟真水波: 噪波波前 x 色散波包 x 高光。", draw_water_ripple),
    ("water_refract", "折射水波: UV 位移采样 x 法线光照。", draw_water_refract),
    ("neon_pulse_stack", "三层预设同相位呼吸堆叠。", draw_neon_pulse_stack),
    ("card_entrance", "入场反馈: 时间轴编排三效果。", draw_card_entrance),
    ("loading_orbit", "加载指示: 粒子 + 反向 glint + 脉动。", draw_loading_orbit),
]


def showcase_templates() -> list[Template]:
    """All showcase template structures (for renderer warmup in the gallery)."""
    return [
        _TEMPLATES.get("dissolve", _t_dissolve),
        _TEMPLATES.get("flame", _t_flame),
        _TEMPLATES.get("aurora", _t_aurora),
        _TEMPLATES.get("electric", _t_electric),
        _TEMPLATES.get("shield", _t_shield),
        _TEMPLATES.get("glitch", _t_glitch),
        _TEMPLATES.get("vortex", _t_vortex),
        _TEMPLATES.get("flame_dual", _t_flame_dual),
        _TEMPLATES.get("laser_frame", _t_laser_frame),
        _TEMPLATES.get("lava", _t_lava),
        _TEMPLATES.get("hologram", _t_hologram),
        _TEMPLATES.get("interference", _t_interference),
        _TEMPLATES.get("matrix", _t_matrix),
        _TEMPLATES.get("water", _t_water),
        _TEMPLATES.get("water_tex", _t_water_tex),
    ]
