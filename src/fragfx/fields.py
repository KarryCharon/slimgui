"""Field vocabulary: pixel -> scalar mappings (SDFs, distances, projections,
perimeter parameterization) that profiles shape into visible effects."""

from __future__ import annotations

from .core.nodes import FRAG, Const, Expr, ExprLike, Func, Point, wrap
from .core.types import DType
from .math import clamp, dot, length, smooth01

# Corner mask bits for `rounded_rect_sdf_flags` (interpreted by the GLSL
# library function). An empty mask is treated as ALL; NONE forces square
# corners regardless of rounding.
ROUND_CORNERS_TOP_LEFT = 1 << 4
ROUND_CORNERS_TOP_RIGHT = 1 << 5
ROUND_CORNERS_BOTTOM_LEFT = 1 << 6
ROUND_CORNERS_BOTTOM_RIGHT = 1 << 7
ROUND_CORNERS_NONE = 1 << 8
ROUND_CORNERS_ALL = (
    ROUND_CORNERS_TOP_LEFT
    | ROUND_CORNERS_TOP_RIGHT
    | ROUND_CORNERS_BOTTOM_LEFT
    | ROUND_CORNERS_BOTTOM_RIGHT
)


class RoundedRect:
    """Rounded-rect field bundle: SDF, clip mask, perimeter parameter.

    `p_min`/`p_max`/`rounding` may be Python values or `Expr` placeholders
    (template params). Properties cache their node so reuse within one
    effect is emitted once.
    """

    def __init__(self, p_min: ExprLike, p_max: ExprLike, rounding: ExprLike = 0.0):
        self._p_min: Expr = wrap(p_min)
        self._p_max: Expr = wrap(p_max)
        self._rounding: Expr = wrap(rounding)
        self._args = (FRAG, self._p_min, self._p_max, self._rounding)
        self._sdf: Expr | None = None
        self._path_t: Expr | None = None

    @property
    def sdf(self) -> Expr:
        if self._sdf is None:
            self._sdf = Func("rounded_rect_sdf", DType.FLOAT, self._args, ("rounded_rect_sdf",))
        return self._sdf

    @property
    def path_t(self) -> Expr:
        if self._path_t is None:
            self._path_t = Func("rect_path_t", DType.FLOAT, self._args, ("rect_path_t",))
        return self._path_t

    def clip(self, softness: float = 1.5) -> Expr:
        return smooth01(0.0, softness, -self.sdf)

    def uv(self, clamp01: bool = False) -> Expr:
        """Normalized position inside the rect, (0,0) at p_min, (1,1) at p_max."""
        k = (FRAG - self._p_min) / (self._p_max - self._p_min)
        return clamp(k, 0.0, 1.0) if clamp01 else k


def radial_dist(center: ExprLike) -> Expr:
    return length(FRAG - wrap(center))


def linear_proj(origin: ExprLike, direction: ExprLike) -> Expr:
    return dot(FRAG - wrap(origin), wrap(direction))


def rounded_rect_sdf_flags(p_min: ExprLike, p_max: ExprLike, rounding: ExprLike, flags: int) -> Expr:
    """Rounded rect SDF honoring a per-corner mask (compile-time constant);
    see the `ROUND_CORNERS_*` constants."""
    args = (FRAG, wrap(p_min), wrap(p_max), wrap(rounding), Const(int(flags), DType.INT))
    return Func("rounded_rect_sdf_flags", DType.FLOAT, args, ("rounded_rect_sdf_flags",))


__all__ = [
    "Point",
    "ROUND_CORNERS_TOP_LEFT",
    "ROUND_CORNERS_TOP_RIGHT",
    "ROUND_CORNERS_BOTTOM_LEFT",
    "ROUND_CORNERS_BOTTOM_RIGHT",
    "ROUND_CORNERS_NONE",
    "ROUND_CORNERS_ALL",
    "RoundedRect",
    "radial_dist",
    "linear_proj",
    "rounded_rect_sdf_flags",
]
