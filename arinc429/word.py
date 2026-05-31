from __future__ import annotations

from .bitfields import (
    DATA_BITS,
    LABEL_BITS,
    LABELS,
    LSB,
    MSB,
    PARITY_BIT,
    SDI_BITS,
    SSM_BITS,
)
from .datatypes.base import DataFieldType
from .errors import FieldOverflowError


class Word:
    EVEN_PARITY = 0
    ODD_PARITY = 1

    def __init__(self, value: int = 0, parity_type: int = ODD_PARITY) -> None:
        self._value = 0
        self._parity_type = 0
        self.parity_type = parity_type
        self.set_bit_field(LSB, MSB, value)

    def __int__(self) -> int:
        return self._value

    def __format__(self, format_spec: str) -> str:
        return self._value.__format__(format_spec)

    def __index__(self) -> int:
        return self._value

    def __repr__(self) -> str:
        return ("{self.__class__.__qualname__}({self._value:#x})").format(self=self)

    def __str__(self) -> str:
        return (
            "Label={self.label:#o}, SDI={self.sdi}, Data={self.data:#x}, "
            "SSM={self.ssm}, Parity={self.parity}"
        ).format(self=self)

    @property
    def label(self) -> int:
        return LABELS[self.get_bit_field(*LABEL_BITS)]

    @label.setter
    def label(self, value: int) -> None:
        try:
            self.set_bit_field(*LABEL_BITS, LABELS[value])
        except KeyError:
            raise ValueError(
                "Label must be >= {:#o} and <= {:#o}: {:#o}".format(
                    min(LABELS), max(LABELS), value
                )
            )

    @property
    def sdi(self) -> int:
        return self.get_bit_field(*SDI_BITS)

    @sdi.setter
    def sdi(self, value: int) -> None:
        self.set_bit_field(*SDI_BITS, value)

    @property
    def data(self) -> int:
        return self.get_bit_field(*DATA_BITS)

    @data.setter
    def data(self, value: int) -> None:
        self.set_bit_field(*DATA_BITS, value)

    @property
    def ssm(self) -> int:
        return self.get_bit_field(*SSM_BITS)

    @ssm.setter
    def ssm(self, value: int) -> None:
        self.set_bit_field(*SSM_BITS, value)

    @property
    def parity(self) -> int:
        return self.get_bit_field(PARITY_BIT, PARITY_BIT)

    @property
    def parity_type(self) -> int:
        return self._parity_type

    @parity_type.setter
    def parity_type(self, value: int) -> None:
        if value in (self.EVEN_PARITY, self.ODD_PARITY):
            self._parity_type = value
            self.set_bit_field(LSB, MSB, self._value)
        else:
            raise ValueError(
                "Parity setting must be {cls.EVEN_PARITY} or "
                "{cls.ODD_PARITY}: {0}".format(value, cls=self)
            )

    @staticmethod
    def _validate_bit_field_range(lsb: int, msb: int) -> None:
        if lsb < LSB:
            raise ValueError("LSB must be >= {} and <= {}: {}".format(LSB, MSB, lsb))
        elif msb > MSB:
            raise ValueError("MSB must be >= {} and <= {}: {}".format(LSB, MSB, msb))
        elif msb < lsb:
            raise ValueError("MSB must be >= LSB: {}".format(msb))

    @staticmethod
    def _validate_bit_length(bit_length: int, value: int) -> None:
        if bit_length > 0:
            max_value = (1 << bit_length) - 1
            min_value = ~(max_value >> 1)
            if not (min_value <= value <= max_value):
                raise FieldOverflowError(value, bit_length)
        else:
            raise ValueError("Bit length must be > 0")

    def get_bit_field(self, lsb: int, msb: int) -> int:
        self._validate_bit_field_range(lsb, msb)
        bit_field_length = msb - lsb + 1
        bit_field_offset = lsb - 1
        mask = (1 << bit_field_length) - 1
        return (self._value >> bit_field_offset) & mask

    def set_bit_field(self, lsb: int, msb: int, value: int | DataFieldType) -> None:
        self._validate_bit_field_range(lsb, msb)
        bit_field_length = msb - lsb + 1
        self._validate_bit_length(bit_field_length, value)

        bit_field_offset = lsb - 1
        parity_offset = PARITY_BIT - 1

        value_mask = (1 << bit_field_length) - 1
        parity_mask = (1 << parity_offset) - 1
        word_mask = ~(value_mask << bit_field_offset)

        encoded = (value & value_mask) << bit_field_offset
        self._value = (self._value & word_mask) | encoded

        count = format(self, "032b").count("1", 1)
        parity_value = ((count + self._parity_type) % 2) << parity_offset
        self._value = (self._value & parity_mask) | parity_value
