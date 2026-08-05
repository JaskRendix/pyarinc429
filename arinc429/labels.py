from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "LabelInfo",
    "is_valid_label",
    "encode_label",
    "decode_label",
    "reverse_label",
]

ENCODE_LABEL: dict[int, int] = {
    lbl: int(format(lbl, "08b")[::-1], 2) for lbl in range(0o000, 0o400)
}
DECODE_LABEL: dict[int, int] = {wire: lbl for lbl, wire in ENCODE_LABEL.items()}


@dataclass(frozen=True)
class LabelInfo:
    label: int
    wire: int


def is_valid_label(label: int) -> bool:
    """Return True if the label is a valid ARINC 429 octal label."""
    return label in ENCODE_LABEL


def encode_label(label: int) -> int:
    """
    Convert an ARINC 429 label (octal) into its 8-bit wire representation.
    Raises ValueError for invalid labels.
    """
    try:
        return ENCODE_LABEL[label]
    except KeyError as exc:
        raise ValueError(f"Invalid ARINC 429 label: {label:#o}") from exc


def decode_label(wire: int) -> int:
    """
    Convert an 8-bit wire representation into an ARINC 429 label (octal).
    Raises ValueError for invalid wire values.
    """
    try:
        return DECODE_LABEL[wire]
    except KeyError as exc:
        raise ValueError(f"Invalid ARINC 429 wire label: {wire:#x}") from exc


def reverse_label(label: int) -> int:
    """
    Reverse the 8-bit ARINC 429 label bit order.
    Equivalent to the wire-level bit reversal.
    """
    wire = encode_label(label)
    rev = int(f"{wire:08b}"[::-1], 2)
    return decode_label(rev)
