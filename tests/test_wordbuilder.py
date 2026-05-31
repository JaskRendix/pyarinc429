import pytest

from arinc429.builder import WordBuilder
from arinc429.errors import FieldOverflowError
from arinc429.word import Word


def test_builder_creates_default_word():
    w = WordBuilder().build()
    assert isinstance(w, Word)
    assert w.label == 0
    assert w.sdi == 0
    assert w.data == 0
    assert w.ssm == 0
    assert w.parity in (0, 1)


def test_builder_sets_label():
    w = WordBuilder().label(0o123).build()
    assert w.label == 0o123


def test_builder_sets_sdi():
    w = WordBuilder().sdi(2).build()
    assert w.sdi == 2


def test_builder_sets_data():
    w = WordBuilder().data(0x55AA).build()
    assert w.data == 0x55AA


def test_builder_sets_ssm():
    w = WordBuilder().ssm(3).build()
    assert w.ssm == 3


def test_builder_sets_multiple_fields():
    w = WordBuilder().label(0o210).sdi(1).data(0x12345).ssm(2).build()
    assert w.label == 0o210
    assert w.sdi == 1
    assert w.data == 0x12345
    assert w.ssm == 2


def test_builder_respects_parity_type_even():
    w = WordBuilder(parity_type=Word.EVEN_PARITY).build()
    assert w.parity_type == Word.EVEN_PARITY
    assert w.parity in (0, 1)


def test_builder_respects_parity_type_odd():
    w = WordBuilder(parity_type=Word.ODD_PARITY).build()
    assert w.parity_type == Word.ODD_PARITY
    assert w.parity in (0, 1)


def test_builder_does_not_set_unprovided_fields():
    b = WordBuilder()
    b._label = None
    b._sdi = None
    b._data = None
    b._ssm = None
    w = b.build()
    assert w.label == 0
    assert w.sdi == 0
    assert w.data == 0
    assert w.ssm == 0


def test_builder_chainability():
    b = WordBuilder()
    assert b.label(0o123) is b
    assert b.sdi(1) is b
    assert b.data(0x55) is b
    assert b.ssm(2) is b


def test_builder_multiple_builds_independent():
    b = WordBuilder().label(0o123)
    w1 = b.build()
    w2 = b.build()
    assert w1 is not w2
    assert w1.label == w2.label == 0o123


def test_builder_overwrites_previous_values():
    b = WordBuilder().label(0o100)
    b.label(0o200)
    w = b.build()
    assert w.label == 0o200


def test_builder_invalid_label_raises():
    with pytest.raises(ValueError):
        WordBuilder().label(9999).build()


def test_builder_invalid_sdi_raises():
    with pytest.raises(FieldOverflowError):
        WordBuilder().sdi(99).build()


def test_builder_invalid_ssm_raises():
    with pytest.raises(FieldOverflowError):
        WordBuilder().ssm(99).build()


def test_builder_invalid_data_raises():
    with pytest.raises(Exception):
        WordBuilder().data(-999999999999999).build()
