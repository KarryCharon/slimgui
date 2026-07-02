"""The backend-injection seam: a `Dialect` spells the language, the core
stays neutral. Red line: dialects never enter structure keys or `Template`
-- one tree shape shares one key across all backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence

from .core.codegen import GeneratedSource
from .core.nodes import Expr, Func, Tex
from .core.types import DType


class Dialect(ABC):
    """Target-language semantics injected into `core.codegen.generate`."""

    name: str

    @abstractmethod
    def type_name(self, t: DType) -> str:
        """Spelling of a value type (vec3 / float3 / vec3<f32>)."""

    @abstractmethod
    def param_ref(self, t: DType, slot: int, n: int) -> str:
        """Access expression for `n` packed uniform floats starting at `slot`."""

    @abstractmethod
    def emit(self, node: Expr, refs: Sequence[str]) -> str:
        """Expression text for a non-`Param` node, given child references."""

    @abstractmethod
    def lib_sources(self, names: Iterable[str]) -> str:
        """Dependency-ordered library function definitions for this dialect."""

    @abstractmethod
    def assemble(self, gen: GeneratedSource) -> str:
        """Wrap a generated body into a complete shader source."""

    def node_comment(self, node: Expr) -> str | None:
        """Readability annotation for a generated line (never enters keys)."""
        if isinstance(node, Func):
            return node.name
        if isinstance(node, Tex):
            return "texture"
        return None
