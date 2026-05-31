from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import NamedTuple


class BitFieldRange(NamedTuple):
    """A named and typed tuple for specifying the range of a bit field."""

    lsb: int
    msb: int


# Least significant bit (1‑based indexing)
LSB = 1
# Most significant bit
MSB = 32

LABEL_BITS = BitFieldRange(1, 8)
SDI_BITS = BitFieldRange(9, 10)
DATA_BITS = BitFieldRange(11, 29)
SSM_BITS = BitFieldRange(30, 31)
PARITY_BIT = MSB

# Mapping of labels to bit‑reversed labels.
LABELS = {label: int(format(label, "08b")[::-1], 2) for label in range(0o0, 0o400)}


class ARINC429Error(Exception):
    """Base class for ARINC 429 exceptions."""


class FieldOverflowError(ARINC429Error):
    """
    Exception that occurs when attempting to assign a value to a bit field of
    insufficient length.
    """

    def __init__(self, value: int, bit_length: int) -> None:
        super().__init__("{:#x} overflows {} bit(s)".format(value, bit_length))


class DataFieldType(ABC):
    """
    Base class for ARINC 429 data types.

    Defines numeric operations that integrate subclass instances with Word
    instances.
    """

    def __init__(self, value: int = 0) -> None:
        self._value = int(value)

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    # Numeric emulation
    def __lt__(self, other) -> bool:
        return self._value < other if isinstance(other, int) else NotImplemented

    def __le__(self, other) -> bool:
        return self._value <= other if isinstance(other, int) else NotImplemented

    def __gt__(self, other) -> bool:
        return self._value > other if isinstance(other, int) else NotImplemented

    def __ge__(self, other) -> bool:
        return self._value >= other if isinstance(other, int) else NotImplemented

    def __and__(self, other) -> bool:
        return self._value & other if isinstance(other, int) else NotImplemented

    def __int__(self) -> int:
        return self._value

    def __format__(self, spec: str) -> str:
        return self._value.__format__(spec)

    @classmethod
    @abstractmethod
    def decode(cls, **kwargs) -> "DataFieldType":
        _ = kwargs
        return DataFieldType()


class DataField(NamedTuple):
    """A typed, named tuple for specifying data fields."""

    lsb: int
    msb: int
    data: int | DataFieldType


DataFieldValue = int | float | Decimal


class BCD(DataFieldType):
    """Interprets binary coded decimal (BCD) values."""

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


class BNR(DataFieldType):
    """Interprets binary number representation (BNR) values."""

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

        bnr_value = value // resolution
        super().__init__(bnr_value)

        self._decoded_value = bnr_value * resolution
        self._resolution = resolution

    def __int__(self) -> int:
        return int(self._decoded_value)

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


class Discrete(DataFieldType):
    """Interprets discrete values."""

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


class Word:
    """Interprets and validates the composition of a word."""

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
        """Delegate formatting to the underlying integer value."""
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
