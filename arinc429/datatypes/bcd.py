from __future__ import annotations

from decimal import Decimal

from .base import DataFieldType

DataFieldValue = int | float | Decimal


class BCD(DataFieldType):
    PLUS = NORTH = EAST = RIGHT = TO = ABOVE = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    MINUS = SOUTH = WEST = LEFT = FROM = BELOW = 3

    def __init__(
        self, value: DataFieldValue = 0, resolution: DataFieldValue = 1
    ) -> None:
        value = Decimal(str(value))
        resolution = Decimal(str(resolution))

        encoded_value = value // resolution
        minus, digits, _ = encoded_value.as_tuple()

        self._decoded_value = encoded_value * resolution
        self._resolution = resolution
        self._sign = self.MINUS if minus else self.PLUS

        bcd_value = 0
        for digit in digits:
            bcd_value = (bcd_value << 4) | digit

        super().__init__(bcd_value)

    @property
    def decoded(self) -> Decimal:
        return self._decoded_value

    @property
    def encoded(self) -> int:
        return self._value

    @property
    def is_negative(self) -> bool:
        return self._sign == self.MINUS

    def copy(self) -> "BCD":
        return BCD(self._decoded_value, self._resolution)

    def with_resolution(self, new_res: DataFieldValue) -> "BCD":
        return BCD(self._decoded_value, new_res)

    def as_dict(self) -> dict:
        return {
            "type": "BCD",
            "decoded": str(self._decoded_value),
            "encoded": self._value,
            "resolution": str(self._resolution),
            "sign": self._sign,
        }

    def bit_length(self) -> int:
        return self._value.bit_length()

    def __bytes__(self) -> bytes:
        return int(self._value).to_bytes(4, "big")

    def __hash__(self) -> int:
        return hash((self._value, self._resolution))

    def __int__(self) -> int:
        return int(self._decoded_value)

    def __float__(self) -> float:
        return float(self._decoded_value)

    def __repr__(self) -> str:
        return (
            "{self.__class__.__qualname__}(value={self._decoded_value!s}, "
            "resolution={self.resolution})"
        ).format(self=self)

    def __str__(self) -> str:
        return str(self._decoded_value)

    @property
    def resolution(self) -> Decimal:
        return self._resolution

    @property
    def sign(self) -> int:
        return self._sign

    @classmethod
    def decode(
        cls, bcd_value: int, bcd_sign: int, resolution: DataFieldValue = 1
    ) -> "BCD":
        sign = -1 if bcd_sign == cls.MINUS else 1
        int_value = int(format(bcd_value, "x"), 10)
        value = sign * Decimal(int_value) * Decimal(str(resolution))
        return cls(value, resolution)
