"""Internal helpers shared by the vocabulary modules."""

from __future__ import annotations

from .core.nodes import Expr, ExprLike, Func, wrap
from .core.types import DType


def func(name: str, *args: ExprLike, type: DType | None = None, lib: tuple[str, ...] = ()) -> Expr:
    wrapped = tuple(wrap(a) for a in args)
    return Func(name, type or wrapped[0].type, wrapped, lib)
