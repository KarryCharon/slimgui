"""
fragfx: a renderer-agnostic fragment-effect composition framework.

Effects are Python expression DAGs: Python numbers become uniforms
automatically (animation never recompiles), the tree *shape* is the program
cache key, and codegen emits straight-line SSA shader code through a
pluggable `Dialect` (built-in: GLSL). An `Effect` is plain data; how it
reaches a renderer is the host's business (see `contract.md` for the
execution model renderers implement).

Three touchpoints:

1. Build effects -- compose the vocabulary (`fragfx.math` / `fields` /
   `profiles` / `color` / `noise` / `blocks`), or use `fragfx.effects`
   presets; hot paths build a `Template` once and rebind named values.
2. Extend the vocabulary -- `fragfx.lib.register()` + `fragfx.lib.call()`.
3. Implement a backend -- subclass `Dialect`, compile what
   `core.generate()` emits, draw per `contract.md`.

    import fragfx as fx

    rect = fx.fields.RoundedRect(p_min, p_max, rounding)
    sweep = fx.profiles.gauss(fx.profiles.wrap_delta(rect.path_t, t) / 0.1)
    color = fx.color.hsv2rgb(fx.math.fract(rect.path_t), 0.85, 1.0)
    effect = fx.Effect(fx.color.rgba(color, rect.clip() * sweep), p_min, p_max)
"""

from . import blocks as blocks
from . import color as color
from . import effects as effects
from . import fields as fields
from . import glsl as glsl
from . import lib as lib
from . import math as math
from . import noise as noise
from . import profiles as profiles
from .core import (
    FRAG,
    DType,
    Effect,
    Expr,
    ExprLike,
    GeneratedSource,
    Point,
    Template,
    TemplateParams,
    Vec,
    collect_params,
    const,
    generate,
    linearize,
    structure_key,
    wrap,
)
from .dialect import Dialect
from .effects import TemplateStore, preset_templates
from .glsl import dump as dump_glsl
from .lib import MAX_PARTICLES

__version__ = "0.1.0"

__all__ = [
    # vocabulary namespaces
    "math",
    "fields",
    "profiles",
    "color",
    "noise",
    "blocks",
    "effects",
    "lib",
    "glsl",
    # core data model
    "DType",
    "Expr",
    "ExprLike",
    "Point",
    "FRAG",
    "Vec",
    "wrap",
    "const",
    "Effect",
    "Template",
    "TemplateParams",
    "TemplateStore",
    "preset_templates",
    # codegen / backend seam
    "Dialect",
    "GeneratedSource",
    "linearize",
    "structure_key",
    "collect_params",
    "generate",
    "dump_glsl",
    "MAX_PARTICLES",
]
