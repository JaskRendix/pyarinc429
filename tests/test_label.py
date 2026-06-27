import pytest

from arinc429.labels import decode_label, encode_label, is_valid_label, reverse_label


def test_is_valid_label():
    assert is_valid_label(0o001)
    assert is_valid_label(0o377)
    assert not is_valid_label(0o400)


def test_encode_decode_roundtrip():
    for label in [0o001, 0o144, 0o210, 0o377]:
        wire = encode_label(label)
        assert decode_label(wire) == label


def test_encode_invalid_label_raises():
    with pytest.raises(ValueError):
        encode_label(0o400)


@pytest.mark.parametrize("wire", [-1, 256, 999])
def test_decode_invalid_wire_raises(wire):
    with pytest.raises(ValueError):
        decode_label(wire)


def test_reverse_label_roundtrip():
    for label in [0o001, 0o144, 0o210, 0o377]:
        rev = reverse_label(label)
        assert reverse_label(rev) == label


def test_encode_label_bit_reversal():
    # 0o210 = 0b10001000 → reversed = 0b00010001 = 0x11
    assert encode_label(0o210) == 0x11


def test_decode_label_bit_reversal():
    assert decode_label(0x11) == 0o210


def test_reverse_label_is_involution():
    for lbl in [0o001, 0o144, 0o210, 0o377]:
        assert reverse_label(reverse_label(lbl)) == lbl


def test_is_valid_label_range():
    assert is_valid_label(0o000)
    assert is_valid_label(0o377)
    assert not is_valid_label(0o400)
    assert not is_valid_label(-1)
