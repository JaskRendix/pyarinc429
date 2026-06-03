from decimal import Decimal

import pytest

from arinc429 import Word
from arinc429.definitions import EQUIP_ADC, LabelDefinition, decode_word


def test_decode_with_definition_unknown_type_returns_none():
    w = Word()
    # create a fake definition with unknown type
    fake = LabelDefinition(name="X", type="UNKNOWN", resolution=Decimal("1"))
    assert w.decode_with_definition(fake) is None


def test_decode_by_label_missing_label_raises():
    w = Word()
    # label 0 is not present in EQUIP_ADC -> should raise KeyError
    with pytest.raises(KeyError):
        w.decode_by_label(EQUIP_ADC)


def test_definitions_decode_word_returns_none_for_missing():
    w = Word()
    assert decode_word(w, EQUIP_ADC) is None
