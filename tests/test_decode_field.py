"""Tests for the shared per-field decode logic (arinc429.decode)."""

from decimal import Decimal

import pytest

from arinc429.decode import decode_field
from arinc429.definitions import FieldDefinition, LabelDefinition, decode_word
from arinc429.word import Word


def _word_with_field(field: FieldDefinition, raw_value: int) -> Word:
    w = Word()
    w.set_bit_field(field.lsb, field.msb, raw_value)
    return w


def test_decode_field_bnr_positive():
    field = FieldDefinition("alt", 11, 29, "BNR", Decimal("0.5"))
    w = _word_with_field(field, 200)
    decoded = decode_field(w, field)
    assert float(decoded) == 100.0


def test_decode_field_bnr_negative_two_complement():
    # 5-bit field: raw 0b11111 = -1 in two's complement
    field = FieldDefinition("signed", 11, 15, "BNR", Decimal("1.0"))
    w = _word_with_field(field, 0b11111)
    decoded = decode_field(w, field)
    assert float(decoded) == -1.0


def test_decode_field_bcd_sign_from_ssm():
    field = FieldDefinition("bcd_val", 11, 23, "BCD", Decimal("1.0"))
    w = _word_with_field(field, 0x123)  # packed BCD 123
    w.ssm = 0  # PLUS
    assert float(decode_field(w, field)) == 123.0

    w.ssm = 3  # MINUS
    assert float(decode_field(w, field)) == -123.0


def test_decode_field_discrete():
    field = FieldDefinition("status", 11, 12, "DISCRETE")
    w = _word_with_field(field, 0b10)
    decoded = decode_field(w, field)
    assert int(decoded) == 2
    assert decoded.name == "FUNCTIONAL_TEST"


def test_decode_field_unknown_type_returns_none():
    field = FieldDefinition("mystery", 11, 12, "FUTURE_TYPE")
    w = _word_with_field(field, 0b01)
    assert decode_field(w, field) is None


def test_decode_with_definition_matches_decode_word():
    """Word.decode_with_definition and definitions.decode_word must agree."""
    definition = LabelDefinition(
        name="Mixed",
        fields=(
            FieldDefinition("alt", 11, 29, "BNR", Decimal("0.5")),
            FieldDefinition("status", 30, 31, "DISCRETE"),
        ),
    )

    w = Word()
    w.label = 0o203
    w.set_bit_field(11, 29, 0x7FFFF)  # -1 in 19-bit two's complement
    w.ssm = 2

    via_word = w.decode_with_definition(definition)
    via_word_unknown = w.decode_with_definition(definition, report_unknown=True)
    via_definitions = decode_word(w, {0o203: definition})
    assert via_definitions is not None
    via_definitions_fields, _, _ = via_definitions

    assert via_word == via_definitions_fields
    assert via_word_unknown == (via_word, [])
    assert float(via_word["alt"]) == -0.5
    assert int(via_word["status"]) == 2


def test_decode_by_label_uses_shared_logic():
    from arinc429.definitions import EQUIP_ADC

    w = Word()
    w.label = 0o203
    w.data = 100  # 100 feet at resolution 1.0

    decoded = w.decode_by_label(EQUIP_ADC)
    assert float(decoded["altitude"]) == 100.0


def test_decode_field_negative_bnr_not_misread_as_bcd():
    """Regression: the old BNR branch in Word.decode_with_definition carried
    dead BCD code. BNR must be sign-extended via the field width, never
    misinterpreted as packed BCD."""
    field = FieldDefinition("signed", 11, 15, "BNR", Decimal("1.0"))
    w = _word_with_field(field, 0b11111)

    definition = LabelDefinition(name="Signed", fields=(field,))
    decoded = w.decode_with_definition(definition)
    assert float(decoded["signed"]) == -1.0


def test_generate_icd_code_emits_correct_signed_decode(tmp_path):
    """The ICD code generator must emit sign-extending decode calls so the
    generated module decodes negative BNR values correctly."""
    import json

    from arinc429.icd import generate_icd_code

    icd = {
        "labels": [
            {
                "label": "0o203",
                "name": "Pressure Altitude",
                "system": "ADC",
                "category": "Air Data",
                "fields": [
                    {"name": "Altitude", "lsb": 11, "msb": 29, "type": "BNR", "resolution": 1.0},
                    {"name": "Status", "lsb": 30, "msb": 31, "type": "DISCRETE"},
                ],
            }
        ]
    }
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(json.dumps(icd), encoding="utf-8")

    src = generate_icd_code(icd_file)
    assert "BNR.decode(bits_altitude, 19" in src
    assert "Discrete.decode" in src or "Discrete(bits_status)" in src

    ns: dict = {}
    exec(src, ns)  # noqa: S102 - executing generated code in test

    w = Word()
    w.label = 0o203
    w.set_bit_field(11, 29, 0x7FFFF)  # -1 in 19-bit two's complement
    w.set_bit_field(30, 31, 0b10)

    obj = ns["decode_icd_word"](w)
    assert obj is not None
    assert obj.altitude == -1.0
    assert int(obj.status) == 2
