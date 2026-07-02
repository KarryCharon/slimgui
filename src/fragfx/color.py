"""Color vocabulary: colorizers producing the final (or intermediate) rgb/a."""

from __future__ import annotations

from ._util import func as _func
from .core.nodes import Expr, ExprLike, Tex, Vec
from .core.types import DType


def rgba(rgb: ExprLike, a: ExprLike) -> Expr:
    return Vec(rgb, a)


def hsv2rgb(h: ExprLike, s: ExprLike, v: ExprLike) -> Expr:
    return _func("hsv2rgb", h, s, v, type=DType.VEC3, lib=("hsv2rgb",))


def tex(uv: ExprLike) -> Expr:
    """Sample the effect's bound texture (`Effect.texture_id`) at `uv`."""
    return Tex(uv)
