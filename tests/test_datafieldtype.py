import pytest

from arinc429.datatypes.base import DataFieldType


class DummyField(DataFieldType):
    def as_dict(self) -> dict:
        return {"type": "DummyField", "value": self._value}

    @classmethod
    def decode(cls, **kwargs):
        return cls(kwargs.get("value", 0))


def test_datafieldtype_initialization():
    d = DummyField(10)
    assert int(d) == 10


def test_datafieldtype_equality_same_type():
    d1 = DummyField(5)
    d2 = DummyField(5)
    assert d1 == d2


def test_datafieldtype_equality_different_type():
    class OtherField(DataFieldType):
        def as_dict(self) -> dict:
            return {"type": "OtherField", "value": self._value}

        @classmethod
        def decode(cls, **kwargs):
            return cls(kwargs.get("value", 0))

    d1 = DummyField(5)
    d2 = OtherField(5)
    assert d1 != d2


def test_datafieldtype_equality_different_value():
    d1 = DummyField(5)
    d2 = DummyField(6)
    assert d1 != d2


def test_datafieldtype_equality_with_non_datafield_returns_false():
    d = DummyField(5)
    assert d != 5
    assert d != "5"
    assert d != {"value": 5}


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (5, 10, True),
        (10, 5, False),
        (5, 5, False),
    ],
)
def test_datafieldtype_lt(a, b, expected):
    assert (DummyField(a) < b) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (5, 10, True),
        (10, 5, False),
        (5, 5, True),
    ],
)
def test_datafieldtype_le(a, b, expected):
    assert (DummyField(a) <= b) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (10, 5, True),
        (5, 10, False),
        (5, 5, False),
    ],
)
def test_datafieldtype_gt(a, b, expected):
    assert (DummyField(a) > b) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (10, 5, True),
        (5, 10, False),
        (5, 5, True),
    ],
)
def test_datafieldtype_ge(a, b, expected):
    assert (DummyField(a) >= b) == expected


def test_datafieldtype_comparison_with_non_int_returns_notimplemented():
    d = DummyField(5)

    with pytest.raises(TypeError):
        _ = d < "x"

    with pytest.raises(TypeError):
        _ = d <= 3.14

    with pytest.raises(TypeError):
        _ = d > None

    with pytest.raises(TypeError):
        _ = d >= object()


def test_datafieldtype_and_with_int():
    d = DummyField(0b1101)
    assert (d & 0b0101) == (0b1101 & 0b0101)


def test_datafieldtype_and_with_non_int_returns_notimplemented():
    d = DummyField(5)
    with pytest.raises(TypeError):
        _ = d & "x"


def test_datafieldtype_int_conversion():
    d = DummyField(42)
    assert int(d) == 42


def test_datafieldtype_format():
    d = DummyField(255)
    assert format(d, "x") == "ff"


def test_datafieldtype_dict_equality():
    d1 = DummyField(7)
    d2 = DummyField(7)
    assert d1.__dict__ == d2.__dict__


def test_datafieldtype_to_json():
    d = DummyField(42)
    json_str = d.to_json()
    assert '"type": "DummyField"' in json_str
    assert '"value": 42' in json_str


def test_datafieldtype_decode_returns_instance():
    d = DummyField.decode(value=12)
    assert isinstance(d, DummyField)
    assert int(d) == 12


def test_datafieldtype_decode_ignores_unknown_kwargs():
    d = DummyField.decode(value=5, foo=123, bar="ignored")
    assert int(d) == 5


def test_datafieldtype_zero_value():
    d = DummyField(0)
    assert int(d) == 0


def test_datafieldtype_negative_value():
    d = DummyField(-10)
    assert int(d) == -10


def test_datafieldtype_large_value():
    d = DummyField(10**12)
    assert int(d) == 10**12
