import pytest

from arinc429.builder import WordBuilder
from arinc429.errors import FieldOverflowError
from arinc429.word import Word


def test_builder_parity_type_setter():
    b = WordBuilder().parity_type(Word.EVEN_PARITY)
    w = b.build()
    assert w.parity_type == Word.EVEN_PARITY


def test_builder_unknown_field_raises():
    b = WordBuilder()
    # Simulate accidental private attribute added by user code
    b._unexpected = 1
    with pytest.raises(ValueError):
        b.build()


def test_builder_invalid_value_raises_with_context():
    b = WordBuilder().sdi(99)
    with pytest.raises(FieldOverflowError):
        b.build()
