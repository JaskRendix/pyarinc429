import pytest

from arinc429 import Word
from arinc429.definitions import EQUIP_ADC, LabelDefinition
from arinc429.errors import FieldOverflowError


def test_word_validate_passes_for_default_word():
    w = Word()
    # default constructor writes parity; validate should pass
    w.validate()


def test_word_validate_detects_parity_mismatch():
    w = Word()
    # manually flip parity bit to create mismatch by directly setting raw value
    raw = w.raw ^ (1 << 31)
    w._value = raw
    with pytest.raises(ValueError):
        w.validate()


def test_labeldefinition_structure_and_usage():
    # Ensure sample label definitions are present and correctly typed
    assert isinstance(EQUIP_ADC, dict)
    dd = EQUIP_ADC.get(0o203)
    assert isinstance(dd, LabelDefinition)
    assert dd.type == "BNR"
    assert dd.unit == "Feet"


def test_validate_ssm_overflow_raises():
    w = Word()
    # set ssm to an out-of-range value by writing directly to the bit field
    with pytest.raises(FieldOverflowError):
        w.set_bit_field(30, 31, 0xFF)
