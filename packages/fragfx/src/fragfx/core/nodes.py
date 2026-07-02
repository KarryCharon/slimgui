"""Expression AST nodes. Nodes carry *structure only* (tag / children /
uniform values); turning a node into source text is a `Dialect` concern.

Python numbers and tuples in expressions become uniforms (`Param`), not
literals: rebuilding a tree each frame with new values reuses the same
compiled program. Use `const()` to bake a compile-time constant. Reusing
one node object twice emits its subexpression once (DAG-level CSE)."""

from __future__ import annotations

from typing import Union

from .types import DType

Point = tuple[float, float]
#: Anything accepted where an expression is expected: numbers and 2-4 element
#: tuples are lifted to uniforms (`Param`) by `wrap()`.
ExprLike = Union["Expr", float, int, tuple[float, ...], list[float]]


class Expr:
    type: DType = DType.FLOAT
    children: tuple["Expr", ...] = ()
    lib: tuple[str, ...] = ()

    def tag(self) -> tuple:
        """Structural identity of this node (excluding children and values)."""
        return (self.__class__.__name__, self.type)

    def params(self) -> tuple[float, ...]:
        """Uniform values contributed by this node, in slot order."""
        return ()

    # arithmetic sugar -------------------------------------------------------

    def __add__(self, other: ExprLike) -> "Expr":
        return _binop("+", self, other)

    def __radd__(self, other: ExprLike) -> "Expr":
        return _binop("+", other, self)

    def __sub__(self, other: ExprLike) -> "Expr":
        return _binop("-", self, other)

    def __rsub__(self, other: ExprLike) -> "Expr":
        return _binop("-", other, self)

    def __mul__(self, other: ExprLike) -> "Expr":
        return _binop("*", self, other)

    def __rmul__(self, other: ExprLike) -> "Expr":
        return _binop("*", other, self)

    def __truediv__(self, other: ExprLike) -> "Expr":
        return _binop("/", self, other)

    def __rtruediv__(self, other: ExprLike) -> "Expr":
        return _binop("/", other, self)

    def __neg__(self) -> "Expr":
        return UnaryOp("-", self)

    # swizzle sugar ------------------------------------------------------------

    def swizzle(self, fields: str) -> "Expr":
        return Swizzle(self, fields)

    @property
    def x(self) -> "Expr":
        return Swizzle(self, "x")

    @property
    def y(self) -> "Expr":
        return Swizzle(self, "y")

    @property
    def rgb(self) -> "Expr":
        return Swizzle(self, "rgb")

    @property
    def a(self) -> "Expr":
        return Swizzle(self, "a")


class Param(Expr):
    """A uniform leaf: its value can change every frame without recompiling."""

    def __init__(self, values: tuple[float, ...], type: DType):
        self.values: tuple[float, ...] = tuple(float(v) for v in values)
        self.type = type

    def tag(self) -> tuple:
        return ("param", self.type)

    def params(self) -> tuple[float, ...]:
        return self.values


class Const(Expr):
    """A compile-time constant: baked into the source, part of the cache key."""

    def __init__(self, value: float, type: DType = DType.FLOAT):
        self.value = value
        self.type = type

    def tag(self) -> tuple:
        return ("const", self.type, repr(self.value))


class FragPos(Expr):
    """The pixel position being shaded, in display coordinates (y down)."""

    type = DType.VEC2

    def tag(self) -> tuple:
        return ("fragpos",)


class Tex(Expr):
    """Sample the effect's bound texture (`Effect.texture_id`) at `uv`."""

    type = DType.VEC4

    def __init__(self, uv: ExprLike):
        uv = wrap(uv)
        if uv.type is not DType.VEC2:
            raise TypeError(f"tex() uv must be vec2, got {uv.type.code}")
        self.children = (uv,)

    def tag(self) -> tuple:
        return ("tex",)


class BinOp(Expr):
    def __init__(self, op: str, type: DType, a: Expr, b: Expr):
        self.op = op
        self.type = type
        self.children = (a, b)

    def tag(self) -> tuple:
        return ("binop", self.op, self.type)


class UnaryOp(Expr):
    def __init__(self, op: str, a: Expr):
        self.op = op
        self.type = a.type
        self.children = (a,)

    def tag(self) -> tuple:
        return ("unary", self.op, self.type)


class Func(Expr):
    """Call to a shading-language builtin or a registered library function."""

    def __init__(self, name: str, type: DType, args: tuple[Expr, ...], lib: tuple[str, ...] = ()):
        self.name = name
        self.type = type
        self.children = args
        self.lib = lib

    def tag(self) -> tuple:
        return ("func", self.name, self.type)


class Vec(Expr):
    """Constructor like vec4(rgb, a); component sizes must sum to the type."""

    def __init__(self, *components: ExprLike):
        comps = tuple(wrap(c) for c in components)
        if any(c.type is DType.INT for c in comps):
            raise TypeError("vec constructor does not accept int components")
        total = sum(c.type.size for c in comps)
        if total not in (2, 3, 4):
            raise TypeError(f"vec constructor with {total} components")
        self.type = DType.vector(total)
        self.children = comps

    def tag(self) -> tuple:
        return ("vec", self.type)


class Swizzle(Expr):
    def __init__(self, base: Expr, fields: str):
        if base.type.size == 1:
            raise TypeError(f"cannot swizzle a {base.type.code}")
        self.fields = fields
        self.type = DType.vector(len(fields))
        self.children = (base,)

    def tag(self) -> tuple:
        return ("swizzle", self.fields, self.type)


FRAG = FragPos()


def wrap(x: ExprLike) -> Expr:
    if isinstance(x, Expr):
        return x
    if isinstance(x, (int, float)):
        return Param((x,), DType.FLOAT)
    if isinstance(x, (tuple, list)) and 2 <= len(x) <= 4:
        return Param(tuple(x), DType.vector(len(x)))
    raise TypeError(f"cannot use {type(x).__name__} in an effect expression")


def const(x: float) -> Expr:
    return Const(x)


def _binop(op: str, a: ExprLike, b: ExprLike) -> Expr:
    a, b = wrap(a), wrap(b)
    if a.type is DType.INT or b.type is DType.INT:
        raise TypeError("arithmetic on int expressions is not supported")
    if a.type is b.type:
        t = a.type
    elif a.type is DType.FLOAT:
        t = b.type
    elif b.type is DType.FLOAT:
        t = a.type
    else:
        raise TypeError(f"type mismatch: {a.type.code} {op} {b.type.code}")
    return BinOp(op, t, a, b)
