"""Built-in GLSL dialect (desktop OpenGL 3.3 assembly). Other GLSL-family
backends (GLES, Blender `gpu`, Vulkan-GLSL) can subclass and override
`assemble` only; the body and library sources are shared."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from ..core.codegen import GeneratedSource, generate, linearize
from ..core.nodes import BinOp, Const, Expr, FragPos, Func, Swizzle, Tex, UnaryOp, Vec
from ..core.template import Effect, Template
from ..core.types import DType
from ..dialect import Dialect
from ..lib import GLSL_DIALECT, LIBRARY, MAX_PARTICLES

from . import builtins as _builtins  # noqa: F401  (registers the GLSL library sources)


def _fmt_float(v: float) -> str:
    s = f"{v!r}"
    return s if ("." in s or "e" in s) else s + ".0"


class GlslDialect(Dialect):
    name = GLSL_DIALECT

    def type_name(self, t: DType) -> str:
        return t.code

    def param_ref(self, t: DType, slot: int, n: int) -> str:
        if n == 1:
            return f"UParams[{slot}]"
        return f"{t.code}(" + ", ".join(f"UParams[{slot + j}]" for j in range(n)) + ")"

    def emit(self, node: Expr, refs: Sequence[str]) -> str:
        if isinstance(node, Const):
            if node.type is DType.INT:
                return str(int(node.value))
            return _fmt_float(float(node.value))
        if isinstance(node, FragPos):
            return "Frag_Pos"
        if isinstance(node, Tex):
            return f"texture(Texture, {refs[0]})"
        if isinstance(node, BinOp):
            return f"({refs[0]} {node.op} {refs[1]})"
        if isinstance(node, UnaryOp):
            return f"({node.op}{refs[0]})"
        if isinstance(node, Func):
            return f"{node.name}({', '.join(refs)})"
        if isinstance(node, Vec):
            return f"{node.type.code}({', '.join(refs)})"
        if isinstance(node, Swizzle):
            return f"{refs[0]}.{node.fields}"
        raise TypeError(f"GLSL dialect cannot emit {type(node).__name__}")

    def lib_sources(self, names: Iterable[str]) -> str:
        return LIBRARY.sources(names, self.name)

    def assemble(self, gen: GeneratedSource) -> str:
        """Wrap a generated body into a desktop OpenGL 3.3 fragment shader."""
        header = "#version 330\n" + _CONSTS
        header += f"uniform float UParams[{max(gen.n_params, 1)}];\n"
        if gen.uses_texture:
            header += "uniform sampler2D Texture;\n"
        header += "in vec2 Frag_Pos;\nout vec4 Out_Color;\n"
        return header + gen.libs + "\nvoid main() {\n" + gen.body + "\n}\n"


_CONSTS = f"""const float PI = 3.14159265359;
const float HALF_PI = 1.57079632679;
const float GOLDEN_ANGLE = 2.39996322972865332;
const int MAX_PARTICLES = {MAX_PARTICLES};
"""

#: The default dialect instance used by `core.codegen.generate`.
GLSL = GlslDialect()


def assemble_gl330(gen: GeneratedSource) -> str:
    return GLSL.assemble(gen)


def dump(obj: "Effect | Template | Expr") -> str:
    """Generated (OpenGL 3.3) fragment shader source for an effect, template
    or vec4 color expression -- for debugging composed effects. Templates
    annotate their named uniform slots (`UParams[3]; // spread`)."""
    slot_names: dict[int, str] | None = None
    if isinstance(obj, Template):
        color = obj.color
        slot_names = obj.slot_names()
    elif isinstance(obj, Effect):
        color = obj.color
    elif isinstance(obj, Expr):
        color = obj
    else:
        raise TypeError(f"cannot dump {type(obj).__name__}; expected Effect, Template or Expr")
    order, index = linearize(color)
    return GLSL.assemble(generate(order, index, slot_names=slot_names, dialect=GLSL))
