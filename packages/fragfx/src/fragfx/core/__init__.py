"""Language-neutral core: typed AST, linearize/CSE, structure keys, uniform
collection, and the `Template`/`Effect` data model."""

from .codegen import GeneratedSource, collect_params, generate, linearize, structure_key
from .nodes import (
    FRAG,
    BinOp,
    Const,
    Expr,
    ExprLike,
    FragPos,
    Func,
    Param,
    Point,
    Swizzle,
    Tex,
    UnaryOp,
    Vec,
    const,
    wrap,
)
from .template import Effect, Template, TemplateParams
from .types import DType

__all__ = [
    "DType",
    "Expr",
    "ExprLike",
    "Param",
    "Const",
    "FragPos",
    "Tex",
    "BinOp",
    "UnaryOp",
    "Func",
    "Vec",
    "Swizzle",
    "FRAG",
    "Point",
    "wrap",
    "const",
    "linearize",
    "structure_key",
    "collect_params",
    "GeneratedSource",
    "generate",
    "Effect",
    "Template",
    "TemplateParams",
]
