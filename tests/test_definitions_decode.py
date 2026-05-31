from arinc429 import Word
from arinc429.datatypes.bnr import BNR
from arinc429.definitions import EQUIP_ADC, decode_word


def test_decode_word_using_definitions():
    w = Word()
    w.label = 0o203  # EQUIP_ADC entry
    # Set a data value representing 100 feet (resolution=1.0)
    w.data = BNR(100, 1)

    result = decode_word(w, EQUIP_ADC)
    assert result is not None
    data_field, definition = result
    assert definition.name == "Pressure Altitude"
    assert float(data_field) == 100.0
