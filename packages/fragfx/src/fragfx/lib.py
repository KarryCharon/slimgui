"""Library function registry: named source snippets with dependency
resolution, keyed per dialect. Function *names* are dialect-neutral (they
enter structure keys); *sources* are registered per dialect.

Re-registering a (dialect, name) pair is rejected: changing a source would
not invalidate already-compiled programs -- during development edit +
restart (or clear the renderer's program cache) instead."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .core.nodes import Expr, ExprLike, Func, wrap
from .core.types import DType

#: Compile-time particle loop cap; part of the execution contract.
MAX_PARTICLES = 64

GLSL_DIALECT = "glsl"


@dataclass(frozen=True)
class LibraryFunction:
    name: str
    source: str
    deps: tuple[str, ...]


class LibraryRegistry:
    def __init__(self):
        self._functions: dict[tuple[str, str], LibraryFunction] = {}
        self._names: set[str] = set()

    def __contains__(self, name: str) -> bool:
        """True if `name` is registered for any dialect."""
        return name in self._names

    def register(self, name: str, source: str, deps: Sequence[str] = (), dialect: str = GLSL_DIALECT) -> None:
        key = (dialect, name)
        if key in self._functions:
            raise ValueError(f"library function {name!r} is already registered for dialect {dialect!r}")
        for dep in deps:
            if (dialect, dep) not in self._functions:
                raise ValueError(f"library function {name!r} depends on unknown {dep!r} (dialect {dialect!r})")
        self._functions[key] = LibraryFunction(name, source, tuple(deps))
        self._names.add(name)

    def resolve(self, names: Iterable[str], dialect: str = GLSL_DIALECT) -> list[LibraryFunction]:
        """Expand dependencies, dependencies first, each function once."""
        resolved: list[str] = []

        def add(name: str) -> None:
            if name in resolved:
                return
            entry = self._functions.get((dialect, name))
            if entry is None:
                raise KeyError(f"unknown library function {name!r} for dialect {dialect!r}")
            for dep in entry.deps:
                add(dep)
            resolved.append(name)

        for name in names:
            add(name)
        return [self._functions[(dialect, name)] for name in resolved]

    def sources(self, names: Iterable[str], dialect: str = GLSL_DIALECT) -> str:
        return "".join(entry.source for entry in self.resolve(names, dialect))


LIBRARY = LibraryRegistry()


def register(name: str, source: str, deps: Sequence[str] = (), dialect: str = GLSL_DIALECT) -> None:
    """Register a custom library function for use in composed effects.

    `source` must define a function called `name` in the dialect's language
    (private helpers are fine; prefix them with the function name to avoid
    clashes). `deps` lists other library functions the source calls. Call it
    from an expression with `call(name, ret_type, *args)`.
    """
    LIBRARY.register(name, source, deps, dialect)


def call(name: str, ret_type: DType, *args: ExprLike) -> Expr:
    """Call a library function registered with `register()`."""
    if name not in LIBRARY:
        raise KeyError(f"unknown library function {name!r}; register it with fragfx.lib.register()")
    wrapped = tuple(wrap(a) for a in args)
    return Func(name, ret_type, wrapped, (name,))
