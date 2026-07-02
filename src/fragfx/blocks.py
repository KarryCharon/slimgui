"""Block vocabulary: heavyweight library-function building blocks that do
not decompose further (material pad, particle batches). Their output is
still an `Expr` and composes with everything else."""

from __future__ import annotations

from ._util import func as _func
from .core.nodes import FRAG, Expr, ExprLike
from .core.types import DType


def material_pad(
    p_min: ExprLike,
    p_max: ExprLike,
    rounding: ExprLike,
    intensity: ExprLike,
    color: ExprLike,
    thickness: ExprLike,
    angle: ExprLike,
    metallic: ExprLike,
    roughness: ExprLike,
    specular: ExprLike,
    softness: ExprLike,
) -> Expr:
    """Principled-lite material pad (plateau + convex shoulder), returns vec4.

    Arguments may be Python values or `Expr` placeholders (template params).
    """
    args = (
        FRAG,
        p_min,
        p_max,
        rounding,
        intensity,
        color,
        thickness,
        angle,
        metallic,
        roughness,
        specular,
        softness,
    )
    return _func("material_pad", *args, type=DType.VEC4, lib=("material_pad",))


def particles_path(
    p_min: ExprLike,
    p_max: ExprLike,
    rounding: ExprLike,
    progress: ExprLike,
    trail: ExprLike,
    inset: ExprLike,
    count: ExprLike,
    radius: ExprLike,
    intensity: ExprLike,
    color: ExprLike,
) -> Expr:
    """Soft particles flowing along a rounded rect path, returns vec4 (src-over)."""
    args = (FRAG, p_min, p_max, rounding, progress, trail, inset, count, radius, intensity, color)
    return _func("particles_path", *args, type=DType.VEC4, lib=("particles_path",))


def particles_burst(
    center: ExprLike,
    progress: ExprLike,
    count: ExprLike,
    radius: ExprLike,
    spread: ExprLike,
    intensity: ExprLike,
    color: ExprLike,
) -> Expr:
    """Deterministic spark burst streaks from `center`, returns vec4 (src-over)."""
    args = (FRAG, center, progress, count, radius, spread, intensity, color)
    return _func("particles_burst", *args, type=DType.VEC4, lib=("particles_burst",))


def particles_trail(
    start: ExprLike,
    end: ExprLike,
    progress: ExprLike,
    count: ExprLike,
    radius: ExprLike,
    spacing: ExprLike,
    intensity: ExprLike,
    color: ExprLike,
) -> Expr:
    """Trail of soft dots behind a point moving start -> end, returns vec4."""
    args = (FRAG, start, end, progress, count, radius, spacing, intensity, color)
    return _func("particles_trail", *args, type=DType.VEC4, lib=("particles_trail",))
