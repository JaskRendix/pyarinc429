from __future__ import annotations

from .base import DataFieldType


class Discrete(DataFieldType):
    NORMAL_OPERATION = VERIFIED_DATA = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    FAILURE_WARNING = 3

    @property
    def decoded(self) -> int:
        return self._value

    @property
    def encoded(self) -> int:
        return self._value

    def copy(self) -> "Discrete":
        return Discrete(self._value)

    def as_dict(self) -> dict:
        return {
            "type": "Discrete",
            "encoded": self._value,
            "decoded": self._value,
        }

    def bit_length(self) -> int:
        return self._value.bit_length()

    def __bytes__(self) -> bytes:
        return int(self._value).to_bytes(4, "big")

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return ("{self.__class__.__qualname__}(value={self._value:#x})").format(
            self=self
        )

    def __str__(self) -> str:
        return str(self._value)

    @classmethod
    def decode(cls, discrete_value: int) -> "Discrete":
        return cls(discrete_value)
