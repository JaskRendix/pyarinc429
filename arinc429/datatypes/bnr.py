from __future__ import annotations

from decimal import Decimal

from .base import DataFieldType

DataFieldValue = int | float | Decimal


class BNR(DataFieldType):
    PLUS = NORTH = EAST = RIGHT = TO = ABOVE = 0
    MINUS = SOUTH = WEST = LEFT = FROM = BELOW = 1

    FAILURE_WARNING = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    NORMAL_OPERATION = 3

    def __init__(
        self, value: DataFieldValue = 0, resolution: DataFieldValue = 1
    ) -> None:
        value = Decimal(str(value))
        resolution = Decimal(str(resolution))

        if resolution <= 0:
            raise ValueError("BNR resolution must be positive")

        bnr_value = value // resolution
        super().__init__(bnr_value)

        self._decoded_value = bnr_value * resolution
        self._resolution = resolution

    @property
    def decoded(self) -> Decimal:
        return self._decoded_value

    @property
    def encoded(self) -> int:
        return self._value

    @property
    def is_negative(self) -> bool:
        return self._decoded_value < 0

    def copy(self) -> "BNR":
        return BNR(self._decoded_value, self._resolution)

    def with_resolution(self, new_res: DataFieldValue) -> "BNR":
        return BNR(self._decoded_value, new_res)

    def as_dict(self) -> dict:
        return {
            "type": "BNR",
            "decoded": str(self._decoded_value),
            "encoded": self._value,
            "resolution": str(self._resolution),
        }

    def bit_length(self) -> int:
        return self._value.bit_length()

    def __bytes__(self) -> bytes:
        return int(self._value).to_bytes(4, "big")

    def __hash__(self) -> int:
        return hash((self._value, self._resolution))

    def __int__(self) -> int:
        # Return the encoded integer payload (quantized value)
        return int(self._value)

    def __float__(self) -> float:
        return float(self._decoded_value)

    def __repr__(self) -> str:
        return (
            "{self.__class__.__qualname__}(value={self._decoded_value}, "
            "resolution={self.resolution})"
        ).format(self=self)

    def __str__(self) -> str:
        return str(self._decoded_value)

    @property
    def resolution(self) -> Decimal:
        return self._resolution

    @classmethod
    def decode(
        cls, bnr_value: int, bnr_bit_length: int, resolution: DataFieldValue = 1
    ) -> "BNR":
        sign = (bnr_value >> (bnr_bit_length - 1)) & 1
        bnr_value -= sign << bnr_bit_length
        value = bnr_value * resolution
        return cls(value, resolution)
