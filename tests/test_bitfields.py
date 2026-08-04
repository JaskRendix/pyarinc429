import pytest

from arinc429.bitfields import (
    DATA_BITS,
    LABEL_BITS,
    PARITY_BIT,
    SDI_BITS,
    SSM_BITS,
    BitFieldRange,
)


@pytest.mark.parametrize(
    "lsb, msb, expected_width",
    [
        (1, 1, 1),
        (1, 8, 8),
        (9, 10, 2),
        (11, 29, 19),
        (32, 32, 1),
    ]
)
def test_width(lsb, msb, expected_width):
    bf = BitFieldRange(lsb, msb)
    assert bf.width == expected_width


@pytest.mark.parametrize(
    "lsb, msb, expected_mask",
    [
        (1, 1, 0b1),
        (1, 2, 0b11),
        (1, 8, 0xFF),
        (9, 10, 0b11),
        (32, 32, 0b1),
    ]
)
def test_mask(lsb, msb, expected_mask):
    bf = BitFieldRange(lsb, msb)
    assert bf.mask == expected_mask


@pytest.mark.parametrize(
    "lsb, msb, expected_shifted",
    [
        (1, 1, 0b1 << 0),
        (1, 8, 0xFF << 0),
        (9, 10, 0b11 << 8),
        (32, 32, 0b1 << 31),
    ]
)
def test_shifted_mask(lsb, msb, expected_shifted):
    bf = BitFieldRange(lsb, msb)
    assert bf.shifted_mask == expected_shifted


@pytest.mark.parametrize(
    "bf, raw, expected",
    [
        (LABEL_BITS, 0b10101010, 0b10101010),  # label in bits 1–8
        (SDI_BITS, 0b0000001100000000, 0b11),  # bits 9–10
        (DATA_BITS, DATA_BITS.insert(0, 0x12345), 0x12345),
        (SSM_BITS, 0b11 << 29, 0b11),
        (PARITY_BIT, 1 << 31, 1),
    ]
)
def test_extract(bf, raw, expected):
    assert bf.extract(raw) == expected


@pytest.mark.parametrize(
    "bf, raw, value, expected",
    [
        (LABEL_BITS, 0, 0xAA, 0xAA),
        (SDI_BITS, 0, 0b10, 0b10 << 8),
        (DATA_BITS, 0, 0x1FFFF, 0x1FFFF << 10),
        (SSM_BITS, 0xFFFFFFFF, 0b00, 0xFFFFFFFF & ~(0b11 << 29)),
        (PARITY_BIT, 0, 1, 1 << 31),
    ]
)
def test_insert(bf, raw, value, expected):
    assert bf.insert(raw, value) == expected


@pytest.mark.parametrize(
    "bf, value",
    [
        (LABEL_BITS, 0x1FF),  # 9 bits into 8-bit field
        (SDI_BITS, 0b100),    # 3 bits into 2-bit field
        (DATA_BITS, DATA_BITS.mask + 1),
        (PARITY_BIT, 2),
    ]
)
def test_insert_overflow(bf, value):
    with pytest.raises(ValueError):
        bf.insert(0, value)


@pytest.mark.parametrize(
    "bf, value",
    [
        (LABEL_BITS, 0x55),
        (SDI_BITS, 0b01),
        (DATA_BITS, 0x12345),
        (SSM_BITS, 0b10),
        (PARITY_BIT, 1),
    ]
)
def test_round_trip(bf, value):
    raw = 0
    inserted = bf.insert(raw, value)
    extracted = bf.extract(inserted)
    assert extracted == value


def test_zero_width_invalid():
    bf = BitFieldRange(10, 9)
    assert bf.width == 0  # current behavior


def test_full_word_mask():
    bf = BitFieldRange(1, 32)
    assert bf.width == 32
    assert bf.mask == (1 << 32) - 1
    assert bf.shifted_mask == bf.mask  # no shift


def test_insert_preserves_other_bits():
    raw = 0xFFFFFFFF
    bf = BitFieldRange(1, 8)
    new_raw = bf.insert(raw, 0x00)
    assert (new_raw & bf.shifted_mask) == 0
    assert (new_raw >> 8) == (raw >> 8)
