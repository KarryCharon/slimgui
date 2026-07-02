"""Effects and templates: the per-draw data handed to a shader-capable
renderer. `Effect` is a frozen snapshot (color expression + coverage-quad
bounds + packed uniforms); `Template` builds a *structure* once and rebinds
named values per draw, so per-call cost scales with named params only."""

from __future__ import annotations

from dataclasses import dataclass

from .codegen import collect_params, linearize, structure_key
from .nodes import Expr, Param, Point
from .types import DType


@dataclass(frozen=True)
class Effect:
    """A composed effect: final vec4 color expression + coverage quad bounds.

    `p_min`/`p_max` are display coordinates and must already include any
    padding the effect needs to bleed outside its rect (glows etc.).
    `texture_id` must be set when the expression contains `tex()` nodes.
    `key`/`values` are an optional fast path filled in by `Template.effect`:
    when present, the renderer can skip per-draw tree traversal entirely.
    """

    color: Expr
    p_min: Point
    p_max: Point
    texture_id: int | None = None
    key: tuple | None = None
    values: tuple[float, ...] | None = None


class TemplateParams:
    """Declares the named, rebindable uniform slots of a `Template`."""

    def __init__(self):
        self.named: dict[str, Param] = {}

    def _declare(self, name: str, type: DType) -> Param:
        if name in self.named:
            raise ValueError(f"template param {name!r} declared twice")
        param = Param((0.0,) * type.size, type)
        self.named[name] = param
        return param

    def f(self, name: str) -> Param:
        return self._declare(name, DType.FLOAT)

    def vec2(self, name: str) -> Param:
        return self._declare(name, DType.VEC2)

    def vec3(self, name: str) -> Param:
        return self._declare(name, DType.VEC3)

    def vec4(self, name: str) -> Param:
        return self._declare(name, DType.VEC4)


class Template:
    """An effect structure built once, with named values rebound per draw.

    Build the tree with `TemplateParams` placeholders for everything that
    changes per call; anonymous numbers stay frozen at their build-time
    values. `effect()` snapshots a full uniform vector without rebuilding
    or traversing the tree.
    """

    def __init__(self, color: Expr, params: TemplateParams):
        if color.type is not DType.VEC4:
            raise TypeError(f"effect color must be vec4, got {color.type.code}")
        self.color = color
        order, index = linearize(color)
        self.key = structure_key(order, index)

        proto: list[float] = []
        offsets: dict[int, int] = {}
        for node in order:
            if isinstance(node, Param):
                offsets[id(node)] = len(proto)
                proto.extend(node.values)
        self._proto = proto
        unused = [name for name, param in params.named.items() if id(param) not in offsets]
        if unused:
            raise ValueError(f"template params declared but not used in the tree: {unused}")
        self._slots = {
            name: (offsets[id(param)], len(param.values)) for name, param in params.named.items()
        }

    def slot_names(self) -> dict[int, str]:
        """Uniform slot offset -> param name (for codegen annotations)."""
        return {offset: name for name, (offset, _size) in self._slots.items()}

    def effect(self, p_min: Point, p_max: Point, texture_id: int | None = None, /, **values) -> Effect:
        """Snapshot an `Effect` with this structure and the given values.

        The quad bounds (and optional texture) are positional-only so named
        params may reuse those names. Every named param must be provided;
        values are floats or sequences matching the declared size.
        """
        slots = self._slots
        if len(values) != len(slots):
            missing = sorted(slots.keys() - values.keys())
            extra = sorted(values.keys() - slots.keys())
            raise TypeError(f"template values mismatch: missing {missing}, unknown {extra}")
        buf = self._proto.copy()
        for name, value in values.items():
            offset, size = slots[name]
            if size == 1:
                buf[offset] = float(value)
            else:
                for j in range(size):
                    buf[offset + j] = float(value[j])
        return Effect(self.color, p_min, p_max, texture_id, key=self.key, values=tuple(buf))
