import pytest

from arinc429.arinc429 import Discrete


@pytest.mark.parametrize("value", [0, 1, 5, 7, 123])
def test_discrete_basic_int_and_str(value):
    d = Discrete(value)
    assert int(d) == value
    assert str(d) == str(value)


def test_discrete_repr_contains_hex():
    d = Discrete(3)
    r = repr(d)
    assert "Discrete" in r
    assert "0x" in r


@pytest.mark.parametrize("value", [0, 1, 3, 7, 15])
def test_discrete_hash_matches_value(value):
    d = Discrete(value)
    assert hash(d) == hash(value)


@pytest.mark.parametrize(
    "value,expected_bytes",
    [
        (0x00000000, b"\x00\x00\x00\x00"),
        (0x00000001, b"\x00\x00\x00\x01"),
        (0x12345678, b"\x12\x34\x56\x78"),
        (0xFFFFFFFF, b"\xFF\xFF\xFF\xFF"),
    ],
)
def test_discrete_bytes_big_endian(value, expected_bytes):
    d = Discrete(value)
    assert bytes(d) == expected_bytes


def test_discrete_copy_independent():
    d1 = Discrete(2)
    d2 = d1.copy()
    assert int(d1) == int(d2)
    assert d1 is not d2


@pytest.mark.parametrize("value", [0, 1, 7, 9, 255])
def test_discrete_decode_round_trip(value):
    d = Discrete.decode(value)
    assert isinstance(d, Discrete)
    assert int(d) == value


@pytest.mark.parametrize(
    "value,expected_len",
    [
        (0, 0),
        (1, 1),
        (0b10110, 5),
        (0xFFFF, 16),
        (0xFFFFFFFF, 32),
    ],
)
def test_discrete_bit_length(value, expected_len):
    d = Discrete(value)
    assert d.bit_length() == expected_len


@pytest.mark.parametrize("value", [0, 1, 2, 3, 10])
def test_discrete_as_dict_structure(value):
    d = Discrete(value)
    dct = d.as_dict()
    assert dct["type"] == "Discrete"
    assert dct["encoded"] == value
    assert dct["decoded"] == value
