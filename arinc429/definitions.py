from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

DataTypeName = Literal["BNR", "BCD", "DISCRETE"]


@dataclass(frozen=True)
class LabelDefinition:
    name: str
    type: DataTypeName
    resolution: Decimal
    unit: str | None = None


# Example equipment definitions (extend as needed)
EQUIP_ADC: dict[int, LabelDefinition] = {
    0o203: LabelDefinition(
        name="Pressure Altitude",
        type="BNR",
        resolution=Decimal("1.0"),
        unit="Feet",
    ),
    0o210: LabelDefinition(
        name="Airspeed",
        type="BNR",
        resolution=Decimal("0.125"),
        unit="Knots",
    ),
}

EQUIP_IRS: dict[int, LabelDefinition] = {
    0o310: LabelDefinition(
        name="Present Latitude",
        type="BNR",
        resolution=Decimal("0.0001"),
        unit="Degrees",
    ),
    0o311: LabelDefinition(
        name="Present Longitude",
        type="BNR",
        resolution=Decimal("0.0001"),
        unit="Degrees",
    ),
}
