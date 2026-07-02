"""Value types of the expression layer. Language-neutral: dialects map
`DType` to their own spelling (`code` is also the GLSL spelling)."""

from __future__ import annotations

from enum import Enum


class DType(Enum):
    FLOAT = ("float", 1)
    VEC2 = ("vec2", 2)
    VEC3 = ("vec3", 3)
    VEC4 = ("vec4", 4)
    INT = ("int", 1)

    def __init__(self, code: str, size: int):
        self.code = code
        self.size = size

    @staticmethod
    def vector(size: int) -> "DType":
        """float/vec2/vec3/vec4 by component count."""
        try:
            return _VEC_BY_SIZE[size]
        except KeyError:
            raise TypeError(f"no vector type with {size} components") from None

    def __repr__(self) -> str:
        return f"DType.{self.name}"


_VEC_BY_SIZE = {
    1: DType.FLOAT,
    2: DType.VEC2,
    3: DType.VEC3,
    4: DType.VEC4,
}
