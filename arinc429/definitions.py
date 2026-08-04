from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from arinc429.bitfields import DATA_BITS
from arinc429.datatypes.bcd import BCD
from arinc429.datatypes.bnr import BNR
from arinc429.datatypes.discrete import Discrete
from arinc429.labelinfo import LABEL_INFO, LabelInfo
from arinc429.word import Word

DataTypeName = Literal["BNR", "BCD", "DISCRETE"]


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    lsb: int
    msb: int
    type: DataTypeName
    resolution: Decimal | None = None
    unit: str | None = None

    @property
    def width(self) -> int:
        return self.msb - self.lsb + 1


@dataclass(frozen=True)
class LabelDefinition:
    name: str
    fields: tuple[FieldDefinition, ...]
    info: LabelInfo | None = None

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    def validate_word(self, word: Word) -> list[str]:
        errors: list[str] = []

        for field in self.fields:
            errors.extend(validate_field(word, field))

        errors.extend(validate_label_structure(self))

        if self.info:
            errors.extend(validate_metadata(word, self.info))

        return errors

    def decode(
        self, word: Word, report_unknown: bool = False
    ) -> tuple[dict[str, object], LabelDefinition, LabelInfo | None] | tuple[dict[str, object], LabelDefinition, LabelInfo | None, list[str]] | None:
        """Decode a word directly using this label definition."""
        label_key = self.info.label if self.info else word.label
        return decode_word(word, {label_key: self}, report_unknown=report_unknown)


def attach_info(defs: dict[int, LabelDefinition]) -> dict[int, LabelDefinition]:
    out: dict[int, LabelDefinition] = {}

    for lbl, defn in defs.items():
        out[lbl] = LabelDefinition(
            name=defn.name,
            fields=defn.fields,
            info=LABEL_INFO.get(lbl),
        )

    return out


def decode_word(
    word: Word,
    definitions: dict[int, LabelDefinition],
    report_unknown: bool = False,
) -> tuple[dict[str, object], LabelDefinition, LabelInfo | None] | tuple[dict[str, object], LabelDefinition, LabelInfo | None, list[str]] | None:
    """
    Decode a word using a label -> LabelDefinition mapping.

    Returns None if the word's label is not present in `definitions`.

    By default returns (decoded_fields, definition, info), matching prior
    behavior exactly (unknown field types are silently skipped).

    If report_unknown=True, returns
        (decoded_fields, definition, info, unknown_field_names)
    instead, so callers can detect definitions referencing field types
    this version of the library doesn't know how to decode.
    """

    try:
        definition: LabelDefinition = definitions[word.label]
    except KeyError:
        return None

    decoded_fields: dict[str, object] = {}
    unknown_fields: list[str] = []

    for field in definition.fields:
        raw = word.get_bit_field(field.lsb, field.msb)

        if field.type == "BNR":
            decoded = BNR.decode(raw, field.width, field.resolution)
        elif field.type == "BCD":
            decoded = BCD.decode(raw, word.ssm, field.resolution)
        elif field.type == "DISCRETE":
            decoded = Discrete.decode(raw)
        else:
            unknown_fields.append(field.name)
            continue

        decoded_fields[field.name] = decoded

    if report_unknown:
        return decoded_fields, definition, definition.info, unknown_fields
    return decoded_fields, definition, definition.info


def _is_valid_bcd(raw: int) -> bool:
    while raw:
        if (raw & 0xF) > 9:
            return False
        raw >>= 4
    return True


def validate_field(word: Word, field: FieldDefinition) -> list[str]:
    errors: list[str] = []

    if field.lsb < DATA_BITS.lsb or field.msb > DATA_BITS.msb:
        errors.append(f"Field {field.name} out of DATA range")

    if field.lsb > field.msb:
        errors.append(f"Field {field.name} has invalid range (lsb > msb)")

    if field.type in ("BNR", "BCD") and field.resolution is None:
        errors.append(f"Field {field.name} missing resolution")

    raw = word.get_bit_field(field.lsb, field.msb)

    if field.type == "BCD" and not _is_valid_bcd(raw):
        errors.append(f"Field {field.name} contains invalid BCD digits")

    return errors


def validate_label_structure(defn: LabelDefinition) -> list[str]:
    errors: list[str] = []

    ranges = [(f.lsb, f.msb, f.name) for f in defn.fields]

    for i, (lsb1, msb1, name1) in enumerate(ranges):
        for lsb2, msb2, name2 in ranges[i + 1:]:
            if not (msb1 < lsb2 or msb2 < lsb1):
                errors.append(f"Fields {name1} and {name2} overlap")

    names = [f.name for f in defn.fields]
    if len(names) != len(set(names)):
        errors.append("Duplicate field names")

    return errors


def validate_metadata(word: Word, info: LabelInfo) -> list[str]:
    """
    Cross-check the word's actual label against the label recorded in its
    attached LabelInfo. A mismatch means a LabelDefinition was built with
    info for the wrong label -- a wiring bug, not a malformed word.
    """
    errors: list[str] = []
    if word.label != info.label:
        errors.append(
            f"Word label {word.label:#o} does not match "
            f"LabelInfo.label {info.label:#o}"
        )
    return errors


_RAW_EQUIP_ADC: dict[int, LabelDefinition] = {
    0o203: LabelDefinition(
        name="Pressure Altitude",
        fields=(
            FieldDefinition(
                name="altitude",
                lsb=11,
                msb=29,
                type="BNR",
                resolution=Decimal("1.0"),
                unit="Feet",
            ),
        ),
    ),
    0o210: LabelDefinition(
        name="Airspeed",
        fields=(
            FieldDefinition(
                name="airspeed",
                lsb=11,
                msb=29,
                type="BNR",
                resolution=Decimal("0.125"),
                unit="Knots",
            ),
        ),
    ),
}

_RAW_EQUIP_IRS: dict[int, LabelDefinition] = {
    0o310: LabelDefinition(
        name="Present Latitude",
        fields=(
            FieldDefinition(
                name="latitude",
                lsb=11,
                msb=29,
                type="BNR",
                resolution=Decimal("0.0001"),
                unit="Degrees",
            ),
        ),
    ),
    0o311: LabelDefinition(
        name="Present Longitude",
        fields=(
            FieldDefinition(
                name="longitude",
                lsb=11,
                msb=29,
                type="BNR",
                resolution=Decimal("0.0001"),
                unit="Degrees",
            ),
        ),
    ),
}

EQUIP_ADC = attach_info(_RAW_EQUIP_ADC)
EQUIP_IRS = attach_info(_RAW_EQUIP_IRS)
EQUIP_ALL = {**EQUIP_ADC, **EQUIP_IRS}
