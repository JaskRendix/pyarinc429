from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .bitfields import DATA_BITS, LABEL_BITS, LSB, MSB, PARITY_BIT, SDI_BITS, SSM_BITS
from .datatypes.base import DataFieldType
from .errors import FieldOverflowError
from .labels import decode_label, encode_label

if TYPE_CHECKING:
    from .definitions import LabelDefinition


class Word:
    """Interprets and validates the composition of a 32‑bit ARINC 429 word."""

    EVEN_PARITY = 0
    ODD_PARITY = 1

    def __init__(self, value: int = 0, parity_type: int = ODD_PARITY, strict_parity: bool = False) -> None:
        if parity_type not in (self.EVEN_PARITY, self.ODD_PARITY):
            raise ValueError(f"Invalid parity type: {parity_type}")
        self._value = value & 0xFFFFFFFF
        self._parity_type = parity_type
        self._strict_parity = strict_parity

        if self._strict_parity and not self.parity_ok:
            raise ValueError("Parity check failed under strict parity enforcement")

    @classmethod
    def from_int(cls, value: int, parity_type: int = ODD_PARITY, strict_parity: bool = False) -> Word:
        """Create a Word from a raw 32‑bit integer, preserving the stored parity bit."""
        return cls(value, parity_type, strict_parity=strict_parity)

    @classmethod
    def from_hex(cls, hex_str: str, parity_type: int = ODD_PARITY, strict_parity: bool = False) -> Word:
        """Create a Word from a hex string (e.g. '0x12345678')."""
        return cls(int(hex_str, 16), parity_type, strict_parity=strict_parity)

    @classmethod
    def from_bin(cls, bin_str: str, parity_type: int = ODD_PARITY, strict_parity: bool = False) -> Word:
        """Create a Word from a binary string (e.g. '1000...')."""
        cleaned = bin_str.replace("_", "").replace(" ", "")
        return cls(int(cleaned, 2), parity_type, strict_parity=strict_parity)

    def to_int(self) -> int:
        return self._value

    @property
    def raw(self) -> int:
        return self._value

    def copy(self) -> Word:
        return Word(self._value, self._parity_type, strict_parity=self._strict_parity)

    def with_fields(self, **kwargs: Any) -> Word:
        w = self.copy()
        for name, value in kwargs.items():
            setattr(w, name, value)
        return w

    def __int__(self) -> int:
        return self._value

    def __index__(self) -> int:
        return self._value

    def __bool__(self) -> bool:
        return self._value != 0

    def __format__(self, fmt: str) -> str:
        return self._value.__format__(fmt)

    def __repr__(self) -> str:
        return f"Word({self._value:#010x})"

    def __str__(self) -> str:
        return (
            f"Label={self.label:#05o}, SDI={self.sdi}, Data={self.data:#x}, "
            f"SSM={self.ssm}, Parity={self.parity} (OK={self.parity_ok})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Word):
            return NotImplemented
        return self._value == other._value and self._parity_type == other._parity_type

    def __hash__(self) -> int:
        return hash((self._value, self._parity_type))

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "sdi": self.sdi,
            "data": self.data,
            "ssm": self.ssm,
            "parity": self.parity,
            "parity_ok": self.parity_ok,
            "parity_type": self.parity_type,
            "raw": self._value,
        }

    def to_binary_str(self) -> str:
        """Return the 32-bit word as an MSB-first '0'/'1' string, bit 32 first."""
        return f"{self._value:032b}"

    def to_json(self, indent: int | None = None) -> str:
        """Serialize the Word dictionary representation to a JSON string."""
        return json.dumps(self.as_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Word:
        """Build a Word from a dictionary representation."""
        parity_type = d.get("parity_type", cls.ODD_PARITY)

        if "raw" in d:
            return cls.from_int(d["raw"], parity_type=parity_type)

        w = cls(0, parity_type=parity_type)
        if "label" in d:
            w.label = d["label"]
        if "sdi" in d:
            w.sdi = d["sdi"]
        if "data" in d:
            w.data = d["data"]
        if "ssm" in d:
            w.ssm = d["ssm"]
        return w

    @property
    def label(self) -> int:
        wire = self.get_bit_field(LABEL_BITS.lsb, LABEL_BITS.msb)
        return decode_label(wire)

    @label.setter
    def label(self, value: int) -> None:
        encoded = encode_label(value)
        self.set_bit_field(LABEL_BITS.lsb, LABEL_BITS.msb, encoded)

    @property
    def sdi(self) -> int:
        return self.get_bit_field(SDI_BITS.lsb, SDI_BITS.msb)

    @sdi.setter
    def sdi(self, value: int) -> None:
        self.set_bit_field(SDI_BITS.lsb, SDI_BITS.msb, value)

    @property
    def data(self) -> int:
        return self.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)

    @data.setter
    def data(self, value: int) -> None:
        self.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, value)

    @property
    def ssm(self) -> int:
        return self.get_bit_field(SSM_BITS.lsb, SSM_BITS.msb)

    @ssm.setter
    def ssm(self, value: int) -> None:
        self.set_bit_field(SSM_BITS.lsb, SSM_BITS.msb, value)

    @property
    def parity(self) -> int:
        return self.get_bit_field(PARITY_BIT.lsb, PARITY_BIT.msb)

    @property
    def parity_ok(self) -> bool:
        """Check if stored bit 32 parity matches the computed parity of bits 1–31."""
        count = (self._value & ((1 << 31) - 1)).bit_count()
        expected = (count + self._parity_type) % 2
        return expected == self.parity

    @property
    def parity_type(self) -> int:
        return self._parity_type

    @parity_type.setter
    def parity_type(self, value: int) -> None:
        if value not in (self.EVEN_PARITY, self.ODD_PARITY):
            raise ValueError(f"Invalid parity type: {value}")
        self._parity_type = value
        self._recompute_parity()

    @staticmethod
    def _validate_bit_field_range(lsb: int, msb: int) -> None:
        if lsb < LSB or msb > MSB or msb < lsb:
            raise ValueError(f"Invalid bit range {lsb}..{msb}")

    @staticmethod
    def _validate_bit_length(bit_length: int, value: int) -> None:
        """Signed two's-complement range check for generic bitfields."""
        if bit_length <= 0:
            raise ValueError("Bit length must be > 0")

        max_value = (1 << bit_length) - 1
        min_value = ~(max_value >> 1)

        if not (min_value <= value <= max_value):
            raise FieldOverflowError(value, bit_length)

    def validate(self, raise_on_error: bool = True) -> list[str] | None:
        errors: list[str] = []

        try:
            _ = self.label
        except Exception as exc:
            errors.append(str(exc))

        if not (0 <= self.sdi <= 3):
            errors.append(f"SDI out of range: {self.sdi}")
        if not (0 <= self.ssm <= 3):
            errors.append(f"SSM out of range: {self.ssm}")

        data_val = self.data
        max_data = (1 << (DATA_BITS.msb - DATA_BITS.lsb + 1)) - 1
        if not (0 <= data_val <= max_data):
            errors.append(f"DATA out of range: {data_val}")

        if not self.parity_ok:
            errors.append("Parity bit does not match computed parity")

        if raise_on_error:
            if errors:
                raise ValueError("; ".join(errors))
            return None
        return errors

    def get_bit_field(self, lsb: int, msb: int) -> int:
        self._validate_bit_field_range(lsb, msb)
        length = msb - lsb + 1
        offset = lsb - 1
        mask = (1 << length) - 1
        return (self._value >> offset) & mask

    def set_bit_field(self, lsb: int, msb: int, value: int | DataFieldType) -> None:
        self._validate_bit_field_range(lsb, msb)

        if isinstance(value, DataFieldType):
            value = int(value)

        length = msb - lsb + 1
        self._validate_bit_length(length, value)

        offset = lsb - 1
        mask = ((1 << length) - 1) << offset

        self._value &= ~mask
        self._value |= (value & ((1 << length) - 1)) << offset

        self._recompute_parity()

    def _recompute_parity(self) -> None:
        """Recompute bit 32 parity from bits 1–31."""
        parity_offset = PARITY_BIT.lsb - 1
        count = (self._value & ((1 << 31) - 1)).bit_count()
        parity_bit = (count + self._parity_type) % 2

        self._value &= ~(1 << parity_offset)
        self._value |= parity_bit << parity_offset

    def decode_with_definition(
        self, definition: LabelDefinition, report_unknown: bool = False
    ):
        """Decode this ARINC 429 word using a multi-field LabelDefinition."""
        from .decode import decode_field

        decoded_fields: dict[str, object] = {}
        unknown_fields: list[str] = []

        for field in definition.fields:
            decoded = decode_field(self, field)
            if decoded is None:
                unknown_fields.append(field.name)
                continue
            decoded_fields[field.name] = decoded

        if report_unknown:
            return decoded_fields, unknown_fields
        return decoded_fields

    def decode_by_label(self, definitions: dict[int, LabelDefinition]):
        label = self.label
        try:
            definition = definitions[label]
        except KeyError:
            raise KeyError(f"Label {label:#o} not present in definitions")

        return self.decode_with_definition(definition)

    def validate_against(self, definition: LabelDefinition) -> list[str]:
        return definition.validate_word(self)

    def validate_by_label(self, definitions: dict[int, LabelDefinition]) -> list[str]:
        try:
            definition = definitions[self.label]
        except KeyError:
            return [f"Label {self.label:#o} not in definitions"]
        return self.validate_against(definition)
