"""Profile vocabulary: scalar -> alpha curves shaping a field into a band,
glow or sweep."""

from __future__ import annotations

import builtins

from .core.nodes import Expr, ExprLike, wrap
from .math import abs as _abs
from .math import clamp, exp as _exp, max as _max, min as _min, smooth01, step


def gauss(x: ExprLike, k: float = 1.0) -> Expr:
    """exp(-k * x^2): the soft-band profile used all over the mesh vfx."""
    x = wrap(x)
    return _exp(-(wrap(k) * x * x))


def smoothfall(t: ExprLike) -> Expr:
    """(1 - smooth01(0,1,t))^2: the standard glow falloff."""
    f = 1.0 - smooth01(0.0, 1.0, t)
    return f * f


def tent(x: ExprLike) -> Expr:
    """max(0, 1 - |x|): linear band profile."""
    return _max(0.0, 1.0 - _abs(x))


def wrap_delta(a: ExprLike, b: ExprLike) -> Expr:
    """Shortest distance between two positions on a [0,1) cycle."""
    d = _abs(wrap(a) - wrap(b))
    return _min(d, 1.0 - d)


def piecewise_linear(u: ExprLike, knots: list[tuple[ExprLike, float]]) -> Expr:
    """Piecewise-linear profile through `knots` [(x, y), ...] of an `Expr` u.

    Knot positions may be Python floats or `Expr` (e.g. template params);
    knot values must be Python floats (they shape the curve and are usually
    fixed constants). Knot positions must be non-decreasing: degenerate
    segments (dx ~ 0) collapse to steps. Outside the knot range the profile
    holds the first/last y. Built as y0 + sum of clamped ramps, branch-free.
    """
    u = wrap(u)
    xs = [x for x, _ in knots]
    ys = [float(y) for _, y in knots]
    result: Expr | float = ys[0]
    for i in range(len(xs) - 1):
        dy = ys[i + 1] - ys[i]
        if dy == 0.0:
            continue
        dx = xs[i + 1] - xs[i]
        dx = builtins.max(dx, 1e-6) if isinstance(dx, float) else _max(dx, 1e-6)
        result = result + clamp((u - xs[i]) / dx, 0.0, 1.0) * dy
    return wrap(result)


def edge_profile(u: ExprLike, w: ExprLike, a0: float, a1: float, a2: float) -> Expr:
    """The inner edge glow profile: nodes {0, .35w, .72w, w} -> {a0,a1,a2,0},
    zero outside [0, w]. `u` is the inward distance (-sdf); `w` may be a
    Python float or an `Expr`."""
    u = wrap(u)
    profile = piecewise_linear(u, [(0.0, a0), (0.35 * w, a1), (0.72 * w, a2), (w, 0.0)])
    return profile * step(0.0, u)
