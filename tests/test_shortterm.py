import pytest

from arinc429 import Word
from arinc429.definitions import EQUIP_ADC, FieldDefinition, LabelDefinition
from arinc429.errors import FieldOverflowError


def test_word_validate_passes_for_default_word():
    w = Word()
    w.validate()


def test_word_validate_detects_parity_mismatch():
    w = Word()
    raw = w.raw ^ (1 << 31)  # flip parity bit
    w._value = raw
    with pytest.raises(ValueError):
        w.validate()


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
