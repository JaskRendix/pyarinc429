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
        val_dec = Decimal(str(value))
        res_dec = Decimal(str(resolution))

        self._sign = self.MINUS if val_dec < 0 else self.PLUS
        abs_val = abs(val_dec)

        encoded_value = abs_val // res_dec
        _, digits, _ = encoded_value.as_tuple()

        self._decoded_value = val_dec
        self._resolution = res_dec

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
        # Return the encoded integer representation (packed BCD nibbles)
        return int(self._value)

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
        """Decode packed BCD nibbles into a signed engineering value.

        The sign is taken from ``bcd_sign`` (use the word's SSM bits on
        ARINC 429). Nibbles are processed least-significant first; a nibble
        outside 0..9 (invalid BCD digit) is taken at face value so a corrupt
        field degrades gracefully instead of raising mid-decode. Use
        ``definitions.validate_field`` if you need strict digit validation.
        """
        sign = -1 if bcd_sign == cls.MINUS else 1
        int_value = 0
        shift = 0
        while bcd_value:
            nibble = bcd_value & 0xF
            int_value += nibble * (10**shift)
            bcd_value >>= 4
            shift += 1
        value = sign * Decimal(int_value) * Decimal(str(resolution))
        return cls(value, resolution)
