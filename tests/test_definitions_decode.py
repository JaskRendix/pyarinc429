from decimal import Decimal

from arinc429 import Word
from arinc429.datatypes.bnr import BNR
from arinc429.definitions import EQUIP_ADC, decode_word


def test_decode_word_using_definitions():
    w = Word()
    w.label = 0o203  # EQUIP_ADC entry

    # Set a data value representing 100 feet (resolution=1.0)
    w.data = BNR(100, Decimal("1.0"))

    result = decode_word(w, EQUIP_ADC)
    assert result is not None

    decoded_fields, definition = result

    assert definition.name == "Pressure Altitude"
    assert "altitude" in decoded_fields

    altitude = decoded_fields["altitude"]
    assert float(altitude) == 100.0
