from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional, Tuple


# Helper to decode a Word using a provided LabelDefinition mapping
def decode_word(word, definitions) -> Optional[object]:
    """Decode a `Word` using the provided definitions map.

    Returns a tuple `(data_field, definition)` when successful, or `None` if no
    definition exists for the word's label.
    """
    try:
        definition = definitions[word.label]
    except Exception:
        return None

    # Import datatypes lazily to avoid cycles
    from .datatypes.bcd import BCD
    from .datatypes.bnr import BNR
    from .datatypes.discrete import Discrete

    data_val = word.get_bit_field(11, 29)
    if definition.type == "BNR":
        bit_length = 29 - 11 + 1
        decoded = BNR.decode(data_val, bit_length, definition.resolution)
    elif definition.type == "BCD":
        decoded = BCD.decode(data_val, word.ssm, definition.resolution)
    elif definition.type == "DISCRETE":
        decoded = Discrete.decode(data_val)
    else:
        return None

    return decoded, definition


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
