from typing import NamedTuple


class BitFieldRange(NamedTuple):
    lsb: int
    msb: int


LSB = 1
MSB = 32

LABEL_BITS = BitFieldRange(1, 8)
SDI_BITS = BitFieldRange(9, 10)
DATA_BITS = BitFieldRange(11, 29)
SSM_BITS = BitFieldRange(30, 31)
PARITY_BIT = MSB

LABELS = {label: int(format(label, "08b")[::-1], 2) for label in range(0o0, 0o400)}
