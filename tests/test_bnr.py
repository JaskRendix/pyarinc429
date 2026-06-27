from decimal import Decimal

import pytest

from arinc429.datatypes.bnr import BNR


@pytest.mark.parametrize(
    "value,resolution,expected_encoded,expected_decoded",
    [
        (0, 1, 0, 0),
        (10, 1, 10, 10),
        (10, 2, 5, 10),
        (Decimal("12.5"), Decimal("0.5"), 25, Decimal("12.5")),
        (-10, 1, -10, -10),
        (-12.5, 0.5, -25, Decimal("-12.5")),
    ],
)
def test_bnr_constructor_quantization(
    value, resolution, expected_encoded, expected_decoded
):
    b = BNR(value, resolution)
    assert b.encoded == expected_encoded
    assert b.decoded == expected_decoded


def test_bnr_negative_flag():
    b = BNR(-5, 1)
    assert b.is_negative is True
    b2 = BNR(5, 1)
    assert b2.is_negative is False


def test_bnr_resolution_property():
    b = BNR(10, Decimal("0.25"))
    assert b.resolution == Decimal("0.25")


def test_bnr_copy_independent():
    b1 = BNR(10, 1)
    b2 = b1.copy()
    assert b1 is not b2
    assert b1.decoded == b2.decoded
    assert b1.resolution == b2.resolution


def test_bnr_with_resolution():
    b = BNR(10, 1)
    b2 = b.with_resolution(0.5)
    assert b2.decoded == b.decoded
    assert b2.resolution == Decimal("0.5")
    assert b2.encoded == (b.decoded / Decimal("0.5"))


def test_bnr_as_dict():
    b = BNR(12.5, 0.5)
    d = b.as_dict()
    assert d["type"] == "BNR"
    assert d["decoded"] == "12.5"
    assert d["encoded"] == 25
    assert d["resolution"] == "0.5"


def test_bnr_repr_and_str():
    b = BNR(10, 1)
    assert "BNR" in repr(b)
    assert str(b) == "10"


def test_bnr_bytes():
    b = BNR(100, 1)
    assert isinstance(bytes(b), bytes)
    assert len(bytes(b)) == 4


def test_bnr_int_float_bit_length():
    b = BNR(12.5, 0.5)  # encoded = 25
    assert int(b) == 25
    assert float(b) == 12.5
    assert b.bit_length() == (25).bit_length()


@pytest.mark.parametrize(
    "raw,bitlen,resolution,expected",
    [
        (0b0000000000000000000, 19, 1, 0),
        (0b0000000000000001010, 19, 1, 10),
        (0b1000000000000000000, 19, 1, -(1 << 18)),  # sign bit set
        (0b0000000000000001010, 19, 0.5, 5),
        (0b1111111111111111111, 19, 1, -1),  # two's complement wrap
    ],
)
def test_bnr_decode(raw, bitlen, resolution, expected):
    b = BNR.decode(raw, bitlen, resolution)
    assert float(b.decoded) == float(expected)


def test_bnr_zero_resolution_invalid():
    with pytest.raises(Exception):
        BNR(10, 0)


def test_bnr_large_values():
    b = BNR(1_000_000, 0.1)
    assert float(b.decoded) == 1_000_000


def test_bnr_decimal_inputs():
    b = BNR(Decimal("12.345"), Decimal("0.005"))
    assert b.decoded == Decimal("12.345")


def test_bnr_float_inputs():
    b = BNR(12.75, 0.25)
    assert float(b.decoded) == 12.75


def test_bnr_negative_resolution_invalid():
    with pytest.raises(Exception):
        BNR(10, -1)
