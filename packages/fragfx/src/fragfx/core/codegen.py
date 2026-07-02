"""Dialect-driven code generation from expression trees.

Invariants: `structure_key` hashes tree *shape* only (same shape = same
cached program, uniform values free to change per frame) and is dialect
independent; `generate` emits straight-line SSA with no runtime branching;
readability comments never affect the key."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .nodes import Expr, Param, Tex
from .types import DType

if TYPE_CHECKING:
    from ..dialect import Dialect


def linearize(root: Expr) -> tuple[list[Expr], dict[int, int]]:
    """Post-order unique-node traversal; shared subtrees appear once."""
    order: list[Expr] = []
    index: dict[int, int] = {}

    def visit(node: Expr) -> None:
        if id(node) in index:
            return
        for child in node.children:
            visit(child)
        index[id(node)] = len(order)
        order.append(node)

    visit(root)
    return order, index


def structure_key(order: list[Expr], index: dict[int, int]) -> tuple:
    return tuple(node.tag() + tuple(index[id(child)] for child in node.children) for node in order)


def collect_params(order: list[Expr]) -> list[float]:
    return [value for node in order for value in node.params()]


@dataclass(frozen=True)
class GeneratedSource:
    """Shader body plus the metadata a dialect needs to wrap it."""

    body: str  # statements of main(), including the final `Out_Color = ...;`
    libs: str  # library function definitions (dependency-ordered)
    n_params: int
    uses_texture: bool


def generate(
    order: list[Expr],
    index: dict[int, int],
    slot_names: dict[int, str] | None = None,
    comments: bool = True,
    dialect: "Dialect | None" = None,
) -> GeneratedSource:
    """Generate the shader body for `dialect` (default: built-in GLSL).

    `slot_names` (uniform slot offset -> name, see `Template.slot_names()`)
    annotates named params in the emitted source. Comments are for human
    readers only and play no part in program caching.
    """
    if dialect is None:
        from ..glsl import GLSL as dialect  # built-in default

    if order[-1].type is not DType.VEC4:
        raise TypeError(f"effect color must be vec4, got {order[-1].type.code}")

    lib_names: list[str] = []
    uses_texture = False
    for node in order:
        for name in node.lib:
            if name not in lib_names:
                lib_names.append(name)
        if isinstance(node, Tex):
            uses_texture = True

    lines: list[str] = []
    refs: list[str] = []
    slot = 0
    for i, node in enumerate(order):
        comment = None
        if isinstance(node, Param):
            n = len(node.values)
            value = dialect.param_ref(node.type, slot, n)
            if slot_names is not None:
                comment = slot_names.get(slot)
            slot += n
        else:
            value = dialect.emit(node, [refs[index[id(child)]] for child in node.children])
            comment = dialect.node_comment(node)
        suffix = f"  // {comment}" if comments and comment else ""
        lines.append(f"    {dialect.type_name(node.type)} v{i} = {value};{suffix}")
        refs.append(f"v{i}")

    body = "\n".join(lines) + f"\n    Out_Color = {refs[-1]};"
    libs = dialect.lib_sources(lib_names)
    return GeneratedSource(body=body, libs=libs, n_params=slot, uses_texture=uses_texture)
