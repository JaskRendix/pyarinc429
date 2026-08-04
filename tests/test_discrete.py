import pytest

from arinc429.datatypes.discrete import Discrete


@pytest.mark.parametrize(
    "value,decoded,encoded,name",
    [
        (0, 0, 0, "NORMAL_OPERATION"),
        (1, 1, 1, "NO_COMPUTED_DATA"),
        (2, 2, 2, "FUNCTIONAL_TEST"),
        (3, 3, 3, "FAILURE_WARNING"),
        (4, 4, 4, "UNKNOWN"),
        (99, 99, 99, "UNKNOWN"),
        (-1, -1, -1, "UNKNOWN"),
    ],
)
def test_discrete_decoded_encoded_name(value, decoded, encoded, name):
    d = Discrete(value)
    assert d.decoded == decoded
    assert d.encoded == encoded
    assert d.name == name


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, True),
        (1, True),
        (2, True),
        (3, True),
        (4, False),
        (10, False),
        (-1, False),
    ],
)
def test_discrete_is_valid(value, expected):
    assert Discrete(value).is_valid() == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 0),  # 4 & 3 = 0
        (5, 1),  # 5 & 3 = 1
        (6, 2),  # 6 & 3 = 2
        (7, 3),  # 7 & 3 = 3
        (255, 3),  # 255 & 3 = 3
    ],
)
def test_discrete_clamp(value, expected):
    d = Discrete(value).clamp()
    assert isinstance(d, Discrete)
    assert int(d) == expected


@pytest.mark.parametrize(
    "value,width,expected",
    [
        (0b1010, 2, 0b10),
        (0b1010, 3, 0b010),
        (0b1010, 4, 0b1010),
        (0b1111, 1, 0b1),
        (0b1111, 8, 0b1111),
    ],
)
def test_discrete_to_bits(value, width, expected):
    d = Discrete(value)
    assert d.to_bits(width) == expected


@pytest.mark.parametrize(
    "name,value",
    [
        ("NORMAL_OPERATION", 0),
        ("NO_COMPUTED_DATA", 1),
        ("FUNCTIONAL_TEST", 2),
        ("FAILURE_WARNING", 3),
    ],
)
def test_discrete_from_name(name, value):
    d = Discrete.from_name(name)
    assert isinstance(d, Discrete)
    assert int(d) == value


def test_discrete_from_name_invalid():
    with pytest.raises(ValueError):
        Discrete.from_name("NOT_A_REAL_NAME")


def test_discrete_copy_independent():
    d1 = Discrete(2)
    d2 = d1.copy()
    assert d1 is not d2
    assert int(d1) == int(d2)


def test_discrete_as_dict():
    d = Discrete(2)
    dct = d.as_dict()
    assert dct["type"] == "Discrete"
    assert dct["encoded"] == 2
    assert dct["decoded"] == 2
    assert dct["name"] == "FUNCTIONAL_TEST"


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 2),
        (4, 3),
        (255, 8),
    ],
)
def test_discrete_bit_length(value, expected):
    assert Discrete(value).bit_length() == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, b"\x00\x00\x00\x00"),
        (1, b"\x00\x00\x00\x01"),
        (0x12345678, b"\x12\x34\x56\x78"),
        (0xFFFFFFFF, b"\xFF\xFF\xFF\xFF"),
    ],
)
def test_discrete_bytes(value, expected):
    assert bytes(Discrete(value)) == expected


def test_discrete_repr_and_str():
    d = Discrete(3)
    assert "Discrete" in repr(d)
    assert "0x" in repr(d)
    assert str(d) == "3"
