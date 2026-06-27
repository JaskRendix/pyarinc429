import pytest

from arinc429.api import decode, decode_and_validate, validate
from arinc429.word import Word


def test_api_decode_known_label():
    # Build a valid Pressure Altitude word (label 0o203)
    w = Word()
    w.label = 0o203
    w.data = 100  # altitude = 100 feet

    result = decode(int(w))

    assert result is not None
    decoded_fields, definition, info = result

    assert "altitude" in decoded_fields
    assert float(decoded_fields["altitude"]) == 100.0
    assert definition.name == "Pressure Altitude"
    assert info.system == "ADC"


def test_api_decode_unknown_label():
    w = Word()
    w.label = 0o001  # valid ARINC 429 label, but unknown to EQUIP_ADC/EQUIP_IRS  # not in EQUIP_ADC or EQUIP_IRS

    result = decode(int(w))
    assert result is None


def test_api_validate_ok():
    w = Word()
    w.label = 0o210  # Airspeed
    w.data = 80  # 80 * 0.125 = 10 knots (valid)

    errors = validate(int(w))
    assert errors == []


def test_api_validate_unknown_label():
    w = Word()
    w.label = 0o001  # valid ARINC 429 label, but unknown to EQUIP_ADC/EQUIP_IRS

    errors = validate(int(w))
    assert len(errors) == 1
    assert "not in definitions" in errors[0]


def test_api_decode_and_validate_ok():
    w = Word()
    w.label = 0o310  # Present Latitude
    w.data = 123456  # 12.3456 degrees

    decoded, errors = decode_and_validate(int(w))

    assert errors == []
    assert decoded is not None

    decoded_fields, definition, info = decoded
    assert "latitude" in decoded_fields
    assert pytest.approx(float(decoded_fields["latitude"]), rel=1e-6) == 12.3456
    assert definition.name == "Present Latitude"
    assert info.system == "IRS"


def test_api_decode_and_validate_unknown_label():
    w = Word()
    w.label = 0o001  # valid ARINC 429 label, but unknown to EQUIP_ADC/EQUIP_IRS

    decoded, errors = decode_and_validate(int(w))

    assert decoded is None
    assert len(errors) == 1
    assert "not in definitions" in errors[0]
