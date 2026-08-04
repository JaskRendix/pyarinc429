from __future__ import annotations

from arinc429.definitions import EQUIP_ALL, LabelDefinition, decode_word, merge_definitions
from arinc429.labelinfo import LabelInfo
from arinc429.word import Word

DEFAULT_DEFINITIONS: dict[int, LabelDefinition] = EQUIP_ALL

DecodeResult = (
    tuple[dict[str, object], LabelDefinition, LabelInfo | None]
    | tuple[dict[str, object], LabelDefinition, LabelInfo | None, list[str]]
    | None
)


def decode(
    raw: int,
    definitions: dict[int, LabelDefinition] = DEFAULT_DEFINITIONS,
    parity_type: int = Word.ODD_PARITY,
    report_unknown: bool = False,
) -> DecodeResult:
    """Decode a raw ARINC 429 integer word using given definitions."""
    w = Word.from_int(raw, parity_type)
    return decode_word(w, definitions, report_unknown=report_unknown)


def validate(
    raw: int,
    definitions: dict[int, LabelDefinition] = DEFAULT_DEFINITIONS,
    parity_type: int = Word.ODD_PARITY,
) -> list[str]:
    """Validate a raw ARINC 429 integer word against label definitions."""
    w = Word.from_int(raw, parity_type)
    return w.validate_by_label(definitions)


def decode_and_validate(
    raw: int,
    definitions: dict[int, LabelDefinition] = DEFAULT_DEFINITIONS,
    parity_type: int = Word.ODD_PARITY,
    report_unknown: bool = False,
) -> tuple[DecodeResult, list[str]]:
    """Decode and validate a raw ARINC 429 integer word simultaneously."""
    w = Word.from_int(raw, parity_type)
    decoded = decode_word(w, definitions, report_unknown=report_unknown)
    errors = w.validate_by_label(definitions)
    return decoded, errors


def combine_definitions(*equip_sets: dict[int, LabelDefinition]) -> dict[int, LabelDefinition]:
    """Combine multiple equipment definition sets into a single unified map.

    Convenience wrapper around definitions.merge_definitions.
    """
    return merge_definitions(*equip_sets)
