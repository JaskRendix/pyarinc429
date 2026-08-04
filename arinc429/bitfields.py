from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BitFieldRange:
    lsb: int
    msb: int
    name: str = "unknown"

    @property
    def width(self) -> int:
        """Number of bits in this field."""
        return self.msb - self.lsb + 1

    @property
    def mask(self) -> int:
        """Bitmask for this field unshifted (aligned to LSB 1)."""
        return (1 << self.width) - 1

    @property
    def shifted_mask(self) -> int:
        """Bitmask shifted to its actual position within the 32-bit word."""
        return self.mask << (self.lsb - 1)

    def extract(self, raw_word: int) -> int:
        """Extract and unshift this field from a raw 32-bit ARINC integer."""
        return (raw_word >> (self.lsb - 1)) & self.mask

    def insert(self, raw_word: int, value: int) -> int:
        """Insert a value into this field within a raw 32-bit ARINC integer."""
        if not (0 <= value <= self.mask):
            raise ValueError(f"Value {value} overflows field '{self.name}' of width {self.width}")
        cleaned_mask = self.shifted_mask
        return (raw_word & ~cleaned_mask) | ((value << (self.lsb - 1)) & cleaned_mask)

    def __int__(self) -> int:
        """Allow coercion/comparison to int using msb (useful for single-bit or legacy checks)."""
        return self.msb

    def __eq__(self, other: object) -> bool:
        if isinstance(other, int):
            return self.msb == other and self.lsb == other
        return super().__eq__(other)


# Core ARINC 429 bit positions

LSB = 1
MSB = 32

LABEL_BITS = BitFieldRange(1, 8, "label")
SDI_BITS = BitFieldRange(9, 10, "sdi")
DATA_BITS = BitFieldRange(11, 29, "data")
SSM_BITS = BitFieldRange(30, 31, "ssm")
PARITY_BIT = BitFieldRange(32, 32, "parity")
