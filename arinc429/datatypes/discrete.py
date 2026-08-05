from __future__ import annotations

from .base import DataFieldType


class Discrete(DataFieldType):
    NORMAL_OPERATION = VERIFIED_DATA = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    FAILURE_WARNING = 3

    _NAME_TO_VAL = {
        "NORMAL_OPERATION": 0,
        "VERIFIED_DATA": 0,
        "NO_COMPUTED_DATA": 1,
        "FUNCTIONAL_TEST": 2,
        "FAILURE_WARNING": 3,
    }
    _VAL_TO_NAME = {
        0: "NORMAL_OPERATION",
        1: "NO_COMPUTED_DATA",
        2: "FUNCTIONAL_TEST",
        3: "FAILURE_WARNING",
    }

    @property
    def decoded(self) -> int:
        return self._value

    @property
    def encoded(self) -> int:
        return self._value

    @property
    def name(self) -> str:
        return self._VAL_TO_NAME.get(self._value, "UNKNOWN")

    def is_valid(self) -> bool:
        return 0 <= self._value <= 3

    def clamp(self) -> "Discrete":
        return Discrete(self._value & 0b11)

    def to_bits(self, width: int = 2) -> int:
        return self._value & ((1 << width) - 1)

    def copy(self) -> "Discrete":
        return Discrete(self._value)

    def as_dict(self) -> dict:
        return {
            "type": "Discrete",
            "encoded": self._value,
            "decoded": self._value,
            "name": self.name,
        }

    def bit_length(self) -> int:
        return self._value.bit_length()

    def __bytes__(self) -> bytes:
        return int(self._value).to_bytes(4, "big")

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}(value={self._value:#x})"

    def __str__(self) -> str:
        return str(self._value)

    @classmethod
    def decode(cls, discrete_value: int) -> "Discrete":
        return cls(discrete_value)

    @classmethod
    def from_name(cls, name: str) -> "Discrete":
        if name not in cls._NAME_TO_VAL:
            raise ValueError(f"Invalid discrete name: {name}")
        return cls(cls._NAME_TO_VAL[name])
