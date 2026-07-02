"""Measure the per-call Python overhead of fragfx effects (no GPU work).

Covers all three hot paths a frame can take:

  presets   helper call (Python scalar math + template bind) + emit +
            renderer draw-side work (key/values fast path)
  baseline  bare `Template.effect()` rebinding N named params -- isolates
            framework bind cost from helper-side Python math
  adhoc     rebuilding the expression tree every call (no template) --
            the slow path non-template users pay, including the renderer's
            per-draw linearize + structure_key + collect_params

Run: uv run python benchmarks/bench_vfx_python.py
"""

import time

import fragfx
from fragfx import Effect, Template, TemplateParams
from fragfx import color as fxc
from fragfx import effects as fxe
from fragfx import fields as fxf
from fragfx import math as fxm
from fragfx import profiles as fxp


class FakeDrawList:
    """Captures callbacks like imgui.DrawList.add_callback."""

    def __init__(self):
        self.callbacks = []

    def add_callback(self, fn, userdata=None):
        self.callbacks.append((fn, userdata))


def draw_side(fx: Effect):
    """Replicates the renderer's per-draw Python work, minus the GL calls.

    Templated effects hit the precomputed key/values fast path; ad-hoc
    effects pay linearize + structure_key + collect_params here.
    """
    key, values = fx.key, fx.values
    if key is None or values is None:
        order, index = fragfx.linearize(fx.color)
        if key is None:
            key = fragfx.structure_key(order, index)
        if values is None:
            values = fragfx.collect_params(order)
    return key, values


def emit(dl: FakeDrawList, fx: Effect | None):
    if fx is None:
        return
    dl.add_callback(lambda _dl, _cmd, _effect: None, fx)


# -- baseline: bare template bind (8 named params, no helper math) --------------


def _t_baseline() -> Template:
    p = TemplateParams()
    rect = fxf.RoundedRect(p.vec2("p_min"), p.vec2("p_max"), p.f("rounding"))
    band = fxp.tent((rect.sdf + p.f("inset")) / p.f("hw"))
    sweep = fxp.gauss(fxp.wrap_delta(rect.path_t, p.f("progress")) / p.f("half_len"))
    return Template(fxc.rgba(p.vec3("rgb"), band * sweep), p)


_BASELINE = _t_baseline()


def _bind_baseline(dl: FakeDrawList):
    emit(
        dl,
        _BASELINE.effect(
            (10, 10),
            (210, 90),
            p_min=(10, 10),
            p_max=(210, 90),
            rounding=14.0,
            inset=1.5,
            hw=3.0,
            progress=0.4,
            half_len=0.1,
            rgb=(1.0, 0.9, 0.45),
        ),
    )


# -- adhoc: rebuild the tree every call (no template, slow draw path) -----------


def _adhoc(dl: FakeDrawList, progress: float = 0.4):
    rect = fxf.RoundedRect((10, 10), (210, 90), 14.0)
    band = fxp.tent((rect.sdf + 1.5) / 3.0)
    sweep = fxp.gauss(fxp.wrap_delta(rect.path_t, progress) / 0.1)
    color = fxc.hsv2rgb(fxm.fract(rect.path_t), 0.85, 1.0)
    emit(dl, Effect(fxc.rgba(color, band * sweep), (10, 10), (210, 90)))


CASES = {
    # framework baselines
    "template_bind_baseline(8p)": _bind_baseline,
    "adhoc_tree_rebuild": _adhoc,
    # preset helpers (representative sample)
    "soft_glow_rect": lambda dl: emit(dl, fxe.soft_glow_rect((10, 10), (210, 90), rounding=14.0, spread=16.0, intensity=0.5)),
    "shimmer_band": lambda dl: emit(dl, fxe.shimmer_band((10, 10), (210, 90), rounding=14.0, progress=0.4, angle=-0.5)),
    "click_ripple": lambda dl: emit(dl, fxe.click_ripple((10, 10), (210, 90), (90, 50), rounding=14.0, progress=0.4)),
    "neon_tube_border": lambda dl: emit(dl, fxe.neon_tube_border((10, 10), (210, 90), rounding=14.0)),
    "rounded_rect_glint": lambda dl: emit(dl, fxe.rounded_rect_glint((10, 10), (210, 90), rounding=14.0, progress=0.3)),
    "rounded_rect_glint(corners)": lambda dl: emit(dl, fxe.rounded_rect_glint((10, 10), (210, 90), rounding=14.0, progress=0.3, corner_colors=((0.3, 0.9, 1, 1), (1, 0.86, 0.3, 1), (1, 0.36, 0.75, 1), (0.45, 1, 0.5, 1)))),
    "magnetic_edge_glow": lambda dl: emit(dl, fxe.magnetic_edge_glow((10, 10), (210, 90), (260, 50), rounding=14.0)),
    "corner_glints": lambda dl: emit(dl, fxe.corner_glints((10, 10), (210, 90), rounding=18.0, progress=0.4)),
    "glass_pad": lambda dl: emit(dl, fxe.glass_pad((10, 10), (210, 90), rounding=14.0)),
    "path_particles": lambda dl: emit(dl, fxe.path_particles((10, 10), (210, 90), rounding=14.0, progress=0.4)),
    "rounded_image_edge_fade": lambda dl: emit(dl, fxe.rounded_image_edge_fade(1, (10, 10), (210, 90), (0, 0), (1, 1), rounding=14.0, fade=12.0)),
    "rounded_image_linear_gradient": lambda dl: emit(dl, fxe.rounded_image_linear_gradient(1, (10, 10), (210, 90), (0, 0), (1, 1), 45.0, [(0.0, (1, 0, 0, 1)), (1.0, (0, 0, 1, 1))], rounding=14.0)),
    "rounded_image_gradient(4stop)": lambda dl: emit(dl, fxe.rounded_image_linear_gradient(1, (10, 10), (210, 90), (0, 0), (1, 1), 45.0, [(0.0, (1, 0, 0, 1)), (0.33, (1, 1, 0, 1)), (0.66, (0, 1, 1, 1)), (1.0, (0, 0, 1, 1))], rounding=14.0)),
}

N = 2000


def main():
    print(f"{'case':32s} {'emit us':>9s} {'draw us':>9s} {'total us':>9s}")
    total_us = 0.0
    for name, call in CASES.items():
        # warmup (fills any template caches)
        dl = FakeDrawList()
        call(dl)
        _fn, fx = dl.callbacks[0]
        draw_side(fx)

        t0 = time.perf_counter()
        for _ in range(N):
            dl = FakeDrawList()
            call(dl)
        t1 = time.perf_counter()
        _fn, fx = dl.callbacks[0]
        t2 = time.perf_counter()
        for _ in range(N):
            draw_side(fx)
        t3 = time.perf_counter()

        emit_us = (t1 - t0) / N * 1e6
        draw_us = (t3 - t2) / N * 1e6
        total_us += emit_us + draw_us
        print(f"{name:32s} {emit_us:9.1f} {draw_us:9.1f} {emit_us + draw_us:9.1f}")

    print(f"\nsum over {len(CASES)} cases: {total_us:.0f} us/frame-equivalent")


main()
