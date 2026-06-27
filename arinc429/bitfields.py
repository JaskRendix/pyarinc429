from __future__ import annotations

from typing import NamedTuple


class BitFieldRange(NamedTuple):
    lsb: int
    msb: int

    @property
    def width(self) -> int:
        """Number of bits in this field."""
        return self.msb - self.lsb + 1


# Core ARINC 429 bit positions

LSB = 1
MSB = 32

LABEL_BITS = BitFieldRange(1, 8)
SDI_BITS = BitFieldRange(9, 10)
DATA_BITS = BitFieldRange(11, 29)
SSM_BITS = BitFieldRange(30, 31)
PARITY_BIT = MSB
