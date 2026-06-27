from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from arinc429.labelinfo import LABEL_INFO, LabelInfo

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


def attach_info(defs: dict[int, LabelDefinition]) -> dict[int, LabelDefinition]:
    """
    Attach LabelInfo metadata to each LabelDefinition automatically.
    Returns a new dictionary with updated LabelDefinition objects.
    """
    out: dict[int, LabelDefinition] = {}

    for lbl, defn in defs.items():
        out[lbl] = LabelDefinition(
            name=defn.name,
            fields=defn.fields,
            info=LABEL_INFO.get(lbl),
        )

    return out


def decode_word(
    word, definitions
) -> tuple[dict, LabelDefinition, LabelInfo | None] | None:
    """
    Decode a Word using the provided label definitions.
    Returns (decoded_fields, LabelDefinition, LabelInfo | None)
    or None if label is unknown.
    """

    try:
        definition: LabelDefinition = definitions[word.label]
    except KeyError:
        return None

    # Lazy imports to avoid cycles
    from .datatypes.bcd import BCD
    from .datatypes.bnr import BNR
    from .datatypes.discrete import Discrete

    decoded_fields: dict[str, object] = {}

    for field in definition.fields:
        raw = word.get_bit_field(field.lsb, field.msb)

        if field.type == "BNR":
            decoded = BNR.decode(raw, field.width, field.resolution)
        elif field.type == "BCD":
            decoded = BCD.decode(raw, word.ssm, field.resolution)
        elif field.type == "DISCRETE":
            decoded = Discrete.decode(raw)
        else:
            continue

        decoded_fields[field.name] = decoded

    # Return metadata explicitly as the third element
    return decoded_fields, definition, definition.info


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

# Attach metadata automatically
EQUIP_ADC = attach_info(_RAW_EQUIP_ADC)
EQUIP_IRS = attach_info(_RAW_EQUIP_IRS)
