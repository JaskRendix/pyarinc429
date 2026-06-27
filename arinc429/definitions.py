from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


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


def decode_word(word, definitions) -> tuple[dict, LabelDefinition] | None:
    try:
        definition = definitions[word.label]
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

    return decoded_fields, definition


EQUIP_ADC: dict[int, LabelDefinition] = {
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

EQUIP_IRS: dict[int, LabelDefinition] = {
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
