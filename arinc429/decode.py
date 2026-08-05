"""Shared field-decoding logic for ARINC 429 words.

Both :class:`~arinc429.word.Word` (``decode_with_definition``) and
:mod:`arinc429.definitions` (``decode_word``) need to turn a raw bit field
of a word into a typed data value (BNR / BCD / DISCRETE). Keeping that
logic in a single place guarantees both code paths agree on the decoding
rules - BNR sign extension, BCD sign-from-SSM, and discrete passthrough.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .datatypes.bcd import BCD
from .datatypes.bnr import BNR
from .datatypes.discrete import Discrete

if TYPE_CHECKING:
    from .definitions import FieldDefinition
    from .word import Word


def decode_field(word: "Word", field: "FieldDefinition") -> Any | None:
    """Decode a single ICD field from an ARINC 429 word.

    Decoding rules:

    - ``BNR`` fields are two's-complement sign-extended using the field
      width before being scaled by the resolution.
    - ``BCD`` fields use the word's SSM bits as the sign/status matrix,
      which is where ARINC 429 carries the sign for BCD data.
    - ``DISCRETE`` fields are returned as-is.

    Returns ``None`` when the field type is not recognized, so callers can
    report unknown field types instead of crashing.
    """
    raw = word.get_bit_field(field.lsb, field.msb)

    if field.type == "BNR":
        return BNR.decode(raw, field.width, field.resolution)
    if field.type == "BCD":
        return BCD.decode(raw, word.ssm, field.resolution)
    if field.type == "DISCRETE":
        return Discrete.decode(raw)
    return None
