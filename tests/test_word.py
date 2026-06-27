import pytest

from arinc429.bitfields import DATA_BITS
from arinc429.definitions import EQUIP_ADC
from arinc429.errors import FieldOverflowError
from arinc429.word import Word


def test_word_default_initialization():
    w = Word()
    assert isinstance(w, Word)
    assert w.label == 0
    assert w.sdi == 0
    assert w.data == 0
    assert w.ssm == 0
    assert w.parity in (0, 1)


def test_word_from_int_roundtrip():
    raw = 0xA5A5A5A5
    w = Word.from_int(raw)
    assert (w.to_int() & 0x7FFFFFFF) == (raw & 0x7FFFFFFF)


def test_word_raw_property():
    w = Word(0x12345678)
    assert w.raw == 0x12345678


def test_word_label_set_and_get():
    w = Word()
    w.label = 0o123
    assert w.label == 0o123


def test_word_label_invalid_raises():
    w = Word()
    with pytest.raises(ValueError):
        w.label = 0o777  # invalid ARINC label


def test_word_sdi_valid():
    w = Word()
    w.sdi = 2
    assert w.sdi == 2


def test_word_sdi_invalid_raises():
    w = Word()
    with pytest.raises(FieldOverflowError):
        w.sdi = 99


def test_word_ssm_valid():
    w = Word()
    w.ssm = 3
    assert w.ssm == 3


def test_word_ssm_invalid_raises():
    w = Word()
    with pytest.raises(FieldOverflowError):
        w.ssm = 99


def test_word_data_valid():
    w = Word()
    w.data = (1 << 19) - 1
    assert w.data == 0x7FFFF


def test_word_data_invalid_raises():
    w = Word()
    with pytest.raises(FieldOverflowError):
        w.data = -999999999999


def test_word_parity_ok_property():
    w = Word(0x12345678)
    assert isinstance(w.parity_ok, bool)


def test_word_parity_changes_with_parity_type():
    w = Word(0x12345678, parity_type=Word.ODD_PARITY)
    odd_parity = w.parity
    w.parity_type = Word.EVEN_PARITY
    even_parity = w.parity
    assert odd_parity != even_parity


def test_word_parity_bit_count_optimization():
    w = Word(0xFFFFFFFF)
    assert w.parity_ok in (True, False)


def test_word_copy_independent():
    w1 = Word()
    w1.label = 0o123
    w2 = w1.copy()
    assert w1 is not w2
    assert w1.label == w2.label
    w2.label = 0o200
    assert w1.label != w2.label


def test_word_with_fields_updates_multiple():
    w = Word().with_fields(label=0o123, sdi=1, data=0x55, ssm=2)
    assert w.label == 0o123
    assert w.sdi == 1
    assert w.data == 0x55
    assert w.ssm == 2


def test_word_with_fields_invalid_raises():
    with pytest.raises(FieldOverflowError):
        Word().with_fields(sdi=99)


def test_word_as_dict_contains_all_fields():
    w = Word(0x12345678)
    d = w.as_dict()
    assert set(d.keys()) == {
        "label",
        "sdi",
        "data",
        "ssm",
        "parity",
        "parity_type",
        "raw",
    }


def test_word_repr_and_format_and_str():
    w = Word.from_int(0x12345678)
    assert "Word(" in repr(w)
    assert format(w, "x") == format(0x12345678, "x")
    s = str(w)
    assert "Label=" in s
    assert "SDI=" in s
    assert "SSM=" in s


def test_word_get_bit_field_valid():
    w = Word(0xFFFFFFFF)
    assert w.get_bit_field(1, 32) in (0x7FFFFFFF, 0xFFFFFFFF)


def test_word_get_bit_field_invalid_range_low():
    w = Word()
    with pytest.raises(ValueError):
        w.get_bit_field(0, 5)


def test_word_get_bit_field_invalid_range_high():
    w = Word()
    with pytest.raises(ValueError):
        w.get_bit_field(1, 40)


def test_word_get_bit_field_invalid_range_reversed():
    w = Word()
    with pytest.raises(ValueError):
        w.get_bit_field(10, 5)


def test_word_set_bit_field_invalid_range():
    w = Word()
    with pytest.raises(ValueError):
        w.set_bit_field(0, 5, 1)


def test_word_set_bit_field_invalid_bit_length():
    w = Word()
    with pytest.raises(FieldOverflowError):
        w.set_bit_field(11, 12, 0xFF)


def test_word_set_bit_field_accepts_DataFieldType():
    from arinc429.datatypes.base import DataFieldType

    class DummyType(DataFieldType):
        def __int__(self):
            return 5

        @staticmethod
        def decode(*args, **kwargs):
            return 5

    w = Word()
    w.set_bit_field(*DATA_BITS, DummyType())
    assert w.data == 5


def test_set_raw_preserving_parity_recomputes_correct_parity():
    w = Word()
    w._set_raw_preserving_parity(0x12345678)

    count = (0x12345678 & ((1 << 31) - 1)).bit_count()
    expected = (count + w.parity_type) % 2

    assert w.parity == expected


def test_recompute_parity_is_deterministic():
    w = Word.from_int(0x00000000)
    before = w.parity
    w._recompute_parity()
    after = w.parity
    assert before == after


def test_decode_with_definition_unknown_field_type_skipped():
    class FakeField:
        name = "x"
        lsb = 11
        msb = 12
        type = "UNKNOWN"
        resolution = None
        width = 2

    class FakeDef:
        fields = (FakeField(),)

    w = Word()
    decoded = w.decode_with_definition(FakeDef())
    assert decoded == {}


def test_decode_by_label_unknown_label():
    w = Word()
    w.label = 0o001  # valid but not in EQUIP_ADC
    with pytest.raises(KeyError):
        w.decode_by_label(EQUIP_ADC)


def test_validate_against_calls_definition():
    class FakeDef:
        def validate_word(self, word):
            return ["err1", "err2"]

    w = Word()
    assert w.validate_against(FakeDef()) == ["err1", "err2"]


def test_validate_by_label_unknown_label_returns_error_list():
    w = Word()
    w.label = 0o001  # valid but unknown
    errors = w.validate_by_label(EQUIP_ADC)
    assert len(errors) == 1
    assert "not in definitions" in errors[0]


def test_word_validate_noop():
    w = Word()
    assert w.validate() is None
