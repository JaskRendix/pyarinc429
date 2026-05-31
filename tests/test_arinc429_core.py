from decimal import Decimal

import pytest

from arinc429.arinc429 import (
    BCD,
    BNR,
    DATA_BITS,
    LABEL_BITS,
    PARITY_BIT,
    SDI_BITS,
    SSM_BITS,
    BitFieldRange,
    Discrete,
    FieldOverflowError,
    Word,
)


def test_bitfieldrange_values():
    r = BitFieldRange(5, 10)
    assert r.lsb == 5
    assert r.msb == 10


def test_label_bit_reversal_round_trip():
    w = Word()
    for label in [0o1, 0o7, 0o123, 0o377]:
        w.label = label
        assert w.label == label


def test_label_out_of_range():
    w = Word()
    with pytest.raises(ValueError):
        w.label = 0o400  # invalid


def test_sdi_set_get():
    w = Word()
    w.sdi = 2
    assert w.sdi == 2


def test_ssm_set_get():
    w = Word()
    w.ssm = 3
    assert w.ssm == 3


def test_data_set_get():
    w = Word()
    w.data = 0x12345
    assert w.data == 0x12345


def test_set_get_bitfield_basic():
    w = Word()
    w.set_bit_field(11, 15, 0b10101)
    assert w.get_bit_field(11, 15) == 0b10101


def test_set_bitfield_overflow():
    w = Word()
    with pytest.raises(FieldOverflowError):
        w.set_bit_field(11, 12, 0b1111)  # 4 bits into 2-bit field


def test_set_bitfield_negative_two_complement():
    w = Word()
    # 5-bit field: valid range is -16..15
    w.set_bit_field(11, 15, -3)
    assert w.get_bit_field(11, 15) == (2**5 - 3)


def test_invalid_bitfield_range():
    w = Word()
    with pytest.raises(ValueError):
        w.set_bit_field(0, 5, 1)
    with pytest.raises(ValueError):
        w.set_bit_field(5, 40, 1)
    with pytest.raises(ValueError):
        w.set_bit_field(10, 5, 1)


def test_parity_odd_even_switching():
    w = Word(0, parity_type=Word.ODD_PARITY)
    odd_parity = w.parity

    w.parity_type = Word.EVEN_PARITY
    even_parity = w.parity

    assert odd_parity != even_parity


def test_parity_updates_on_data_change():
    w = Word()
    p1 = w.parity
    w.data = 0x12345
    p2 = w.parity
    assert p1 != p2


def test_bcd_basic_encoding():
    b = BCD(121.5, resolution=0.1)
    assert float(b) == 121.5
    assert int(b) == 121


def test_bcd_sign_positive():
    b = BCD(50)
    assert b.sign == BCD.PLUS


def test_bcd_sign_negative():
    b = BCD(-12.3, resolution=0.1)
    assert b.sign == BCD.MINUS


def test_bcd_decode_known_example():
    # Example: 0x1215 with sign PLUS and resolution 0.1 → 121.5
    encoded = 0x1215
    decoded = BCD.decode(encoded, BCD.PLUS, 0.1)
    assert float(decoded) == pytest.approx(121.5)


def test_bnr_basic_encoding():
    b = BNR(90, resolution=0.5)
    assert float(b) == 90.0


def test_bnr_negative_encoding():
    b = BNR(-12.5, resolution=0.5)
    assert float(b) == -12.5


def test_bnr_decode_round_trip():
    value = Decimal("45.25")
    resolution = Decimal("0.25")
    # Encoded integer is value / resolution
    encoded = int(value / resolution)  # 181
    decoded = BNR.decode(encoded, 16, resolution)
    assert float(decoded) == pytest.approx(45.25)


def test_bnr_two_complement_negative_decode():
    # 8-bit signed: -3 encoded as 0b11111101 = 0xFD
    decoded = BNR.decode(0xFD, 8, 1)
    assert float(decoded) == -3


def test_discrete_basic():
    d = Discrete(5)
    assert int(d) == 5
    assert str(d) == "5"


def test_discrete_decode():
    d = Discrete.decode(7)
    assert int(d) == 7


def test_word_str_contains_fields():
    w = Word()
    s = str(w)
    assert "Label=" in s
    assert "SDI=" in s
    assert "Data=" in s
    assert "SSM=" in s
    assert "Parity=" in s


def test_word_repr_format():
    w = Word(0x123456)
    r = repr(w)
    assert "Word" in r
    assert "0x" in r


def test_set_bitfield_at_lsb():
    w = Word()
    w.set_bit_field(1, 1, 1)
    assert w.get_bit_field(1, 1) == 1


def test_set_bitfield_at_msb_minus_parity():
    w = Word()
    w.set_bit_field(30, 31, 3)
    assert w.get_bit_field(30, 31) == 3


def test_parity_bit_is_last_bit():
    w = Word()
    assert PARITY_BIT == 32
    assert w.get_bit_field(32, 32) in (0, 1)
