"""Noise vocabulary. Animate noise by moving `p` (Python-side offset param),
never by changing compile-time constants like `octaves`."""

from __future__ import annotations

from ._util import func as _func
from .core.nodes import Const, Expr, ExprLike, Func, wrap
from .core.types import DType


def noise(p: ExprLike) -> Expr:
    """Smoothly interpolated 2D value noise of a vec2, output in [0, 1]."""
    return _func("value_noise", p, type=DType.FLOAT, lib=("value_noise",))


def simplex(p: ExprLike) -> Expr:
    """2D simplex noise of a vec2, output in ~[-1, 1]."""
    return _func("simplex_noise", p, type=DType.FLOAT, lib=("simplex_noise",))


def fbm(p: ExprLike, octaves: int = 4) -> Expr:
    """Fractal Brownian motion (value-noise octaves) of a vec2, output [0, 1).

    `octaves` (1..8) is a compile-time constant and part of the shader
    cache key.
    """
    if not 1 <= int(octaves) <= 8:
        raise ValueError("fbm octaves must be in 1..8")
    return Func(
        "fbm",
        DType.FLOAT,
        (wrap(p), Const(int(octaves), DType.INT)),
        ("fbm",),
    )
