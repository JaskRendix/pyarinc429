from decimal import Decimal

from arinc429 import Word
from arinc429.datatypes.bnr import BNR
from arinc429.definitions import EQUIP_ADC, EQUIP_IRS, decode_word
from arinc429.labelinfo import LABEL_INFO, LabelInfo


def test_decode_word_using_definitions():
    w = Word()
    w.label = 0o203  # EQUIP_ADC entry

    # Set a data value representing 100 feet (resolution=1.0)
    w.data = BNR(100, Decimal("1.0"))

    result = decode_word(w, EQUIP_ADC)
    assert result is not None

    decoded_fields, definition, info = result

    assert definition.name == "Pressure Altitude"
    assert "altitude" in decoded_fields

    altitude = decoded_fields["altitude"]
    assert float(altitude) == 100.0

    # Metadata checks
    assert isinstance(info, LabelInfo)
    assert info is LABEL_INFO[0o203]
    assert info.system == "ADC"


def test_metadata_attached_to_adc_definitions():
    for lbl in (0o203, 0o210):
        ld = EQUIP_ADC[lbl]
        # info may be None if not in LABEL_INFO, but must be consistent
        if lbl in LABEL_INFO:
            assert ld.info is LABEL_INFO[lbl]
        else:
            assert ld.info is None


def test_metadata_attached_to_irs_definitions():
    for lbl in (0o310, 0o311):
        ld = EQUIP_IRS[lbl]
        if lbl in LABEL_INFO:
            assert ld.info is LABEL_INFO[lbl]
        else:
            assert ld.info is None


def test_labelinfo_is_frozen():
    info = LABEL_INFO[0o203]
    try:
        info.name = "New Name"
        assert False, "LabelInfo must be frozen"
    except Exception:
        pass


def test_decode_word_returns_metadata():
    w = Word()
    w.label = 0o203
    w.data = BNR(50, Decimal("1.0"))

    decoded, definition, info = decode_word(w, EQUIP_ADC)

    assert isinstance(info, (LabelInfo, type(None)))

    if w.label in LABEL_INFO:
        assert info is LABEL_INFO[w.label]


def test_decode_word_unknown_label_returns_none():
    w = Word()
    w.label = 0o001  # valid ARINC 429 label, but not in EQUIP_ADC
    w.data = BNR(10, Decimal("1.0"))

    assert decode_word(w, EQUIP_ADC) is None


def test_decode_word_field_decoding_with_metadata():
    w = Word()
    w.label = 0o203
    w.data = BNR(123, Decimal("1.0"))

    decoded, definition, info = decode_word(w, EQUIP_ADC)

    assert "altitude" in decoded
    assert float(decoded["altitude"]) == 123.0

    assert isinstance(info, LabelInfo)
    assert info.name == "Pressure Altitude"
