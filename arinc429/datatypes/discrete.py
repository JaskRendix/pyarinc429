from __future__ import annotations

from .base import DataFieldType


class Discrete(DataFieldType):
    NORMAL_OPERATION = VERIFIED_DATA = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    FAILURE_WARNING = 3

    def __repr__(self) -> str:
        return ("{self.__class__.__qualname__}(value={self._value:#x})").format(
            self=self
        )

    def __str__(self) -> str:
        return str(self._value)

    @classmethod
    def decode(cls, discrete_value: int) -> "Discrete":
        return cls(discrete_value)
