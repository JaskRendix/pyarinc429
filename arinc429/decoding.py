from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .datatypes.bcd import BCD
from .datatypes.bnr import BNR
from .datatypes.discrete import Discrete

if TYPE_CHECKING:
    from .definitions import FieldDefinition
    from .word import Word


def decode_field(word: Word, field: FieldDefinition) -> Any | None:
    """Decode a single ICD field from an ARINC 429 word into a typed data value.

    Supported types include BNR, BCD, and DISCRETE. Returns None if the field type is unrecognized.
    """
    raw = word.get_bit_field(field.lsb, field.msb)

    if field.type == "BNR":
        return BNR.decode(raw, field.width, field.resolution)
    if field.type == "BCD":
        return BCD.decode(raw, word.ssm, field.resolution)
    if field.type == "DISCRETE":
        return Discrete.decode(raw)
    return None
