import pytest

from arinc429 import Word
from arinc429.definitions import EQUIP_ADC, FieldDefinition, LabelDefinition
from arinc429.errors import FieldOverflowError


def test_word_validate_passes_for_default_word():
    w = Word()
    w.label = 0o101
    assert w.validate() is None


def test_word_validate_detects_parity_mismatch():
    w = Word(0x12345678, parity_type=Word.ODD_PARITY)
    # Force a parity mismatch by flipping bit 32 using bitwise operations via set_bit_field or recreating a mismatched raw integer
    bad_raw = w.raw ^ (1 << 31)

    # Create a word using from_int with strict enforcement or check validation on a manually corrupted raw word
    w_bad = Word.from_int(bad_raw, parity_type=Word.ODD_PARITY)
    with pytest.raises(ValueError, match="Parity bit does not match computed parity"):
        w_bad.validate()


def test_labeldefinition_structure_and_usage():
    ld = EQUIP_ADC[0o203]
    assert isinstance(ld, LabelDefinition)
    assert len(ld.fields) == 1

    f = ld.fields[0]
    assert isinstance(f, FieldDefinition)
    assert f.type == "BNR"
    assert f.unit == "Feet"


def test_validate_ssm_overflow_raises():
    w = Word()
    with pytest.raises(FieldOverflowError):
        w.set_bit_field(30, 31, 0xFF)
