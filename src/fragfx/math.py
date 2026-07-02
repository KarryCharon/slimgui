"""Math vocabulary: thin typed wrappers over shading-language builtins.
Names intentionally shadow Python builtins inside this namespace
(`fx.math.abs`, `fx.math.max`); they operate on expressions, not numbers."""

from __future__ import annotations

from ._util import func as _func
from .core.nodes import Expr, ExprLike, wrap
from .core.types import DType


def abs(x: ExprLike) -> Expr:  # noqa: A001
    return _func("abs", x)


def exp(x: ExprLike) -> Expr:
    return _func("exp", x)


def pow(x: ExprLike, y: ExprLike) -> Expr:  # noqa: A001
    return _func("pow", x, y)


def fract(x: ExprLike) -> Expr:
    return _func("fract", x)


def floor(x: ExprLike) -> Expr:
    return _func("floor", x)


def mod(x: ExprLike, y: ExprLike) -> Expr:
    return _func("mod", x, y)


def sin(x: ExprLike) -> Expr:
    return _func("sin", x)


def cos(x: ExprLike) -> Expr:
    return _func("cos", x)


def min(a: ExprLike, b: ExprLike) -> Expr:  # noqa: A001
    return _func("min", a, b)


def max(a: ExprLike, b: ExprLike) -> Expr:  # noqa: A001
    return _func("max", a, b)


def clamp(x: ExprLike, lo: ExprLike, hi: ExprLike) -> Expr:
    return _func("clamp", x, lo, hi)


def mix(a: ExprLike, b: ExprLike, t: ExprLike) -> Expr:
    return _func("mix", a, b, t)


def step(edge: ExprLike, x: ExprLike) -> Expr:
    return _func("step", edge, x, type=wrap(x).type)


def length(v: ExprLike) -> Expr:
    return _func("length", v, type=DType.FLOAT)


def dot(a: ExprLike, b: ExprLike) -> Expr:
    return _func("dot", a, b, type=DType.FLOAT)


def atan2(y: ExprLike, x: ExprLike) -> Expr:
    return _func("atan", y, x, type=DType.FLOAT)


def smooth01(edge0: ExprLike, edge1: ExprLike, x: ExprLike) -> Expr:
    """smoothstep clamped to [0, 1] (library function, shared everywhere)."""
    return _func("smooth01", edge0, edge1, x, type=DType.FLOAT, lib=("smooth01",))
