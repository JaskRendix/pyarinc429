from __future__ import annotations

from decimal import Decimal
import json

import pytest

from arinc429.decode import decode_field
from arinc429.definitions import (
    FieldDefinition,
    LabelDefinition,
    decode_word,
    validate_field,
    validate_label_structure,
    validate_metadata,
    EQUIP_ADC,
)
from arinc429.word import Word


def _word_with_field(field: FieldDefinition, raw_value: int) -> Word:
    w = Word()
    w.set_bit_field(field.lsb, field.msb, raw_value)
    return w


@pytest.mark.parametrize(
    "raw,width,resolution,expected",
    [
        (0, 5, Decimal("1.0"), 0.0),
        (1, 5, Decimal("0.5"), 0.5),
        (200, 19, Decimal("0.5"), 100.0),
    ],
)
def test_decode_field_bnr_positive(raw, width, resolution, expected):
    field = FieldDefinition("bnr_val", 11, 11 + width - 1, "BNR", resolution)
    w = _word_with_field(field, raw)
    decoded = decode_field(w, field)
    assert pytest.approx(float(decoded), rel=1e-6) == expected


def test_decode_field_bnr_negative_two_complement():
    # 5-bit field: raw 0b11111 = -1 in two's complement
    field = FieldDefinition("signed", 11, 15, "BNR", Decimal("1.0"))
    w = _word_with_field(field, 0b11111)
    decoded = decode_field(w, field)
    assert float(decoded) == -1.0


@pytest.mark.parametrize(
    "raw_bcd,ssm,resolution,expected",
    [
        (0x123, 0, Decimal("1.0"), 123.0),   # PLUS
        (0x123, 3, Decimal("1.0"), -123.0),  # MINUS
        (0x0,   0, Decimal("1.0"), 0.0),
    ],
)
def test_decode_field_bcd_sign_from_ssm(raw_bcd, ssm, resolution, expected):
    field = FieldDefinition("bcd_val", 11, 23, "BCD", resolution)
    w = _word_with_field(field, raw_bcd)
    w.ssm = ssm
    decoded = decode_field(w, field)
    assert pytest.approx(float(decoded), rel=1e-6) == expected


def test_decode_field_discrete_basic():
    field = FieldDefinition("status", 11, 12, "DISCRETE")
    w = _word_with_field(field, 0b10)
    decoded = decode_field(w, field)
    assert int(decoded) == 2
    assert hasattr(decoded, "name")


@pytest.mark.parametrize("raw", [0b00, 0b01, 0b10, 0b11])
def test_decode_field_discrete_all_values(raw):
    field = FieldDefinition("status", 11, 12, "DISCRETE")
    w = _word_with_field(field, raw)
    decoded = decode_field(w, field)
    assert int(decoded) == raw


def test_decode_field_unknown_type_returns_none():
    field = FieldDefinition("mystery", 11, 12, "FUTURE_TYPE")
    w = _word_with_field(field, 0b01)
    assert decode_field(w, field) is None


def test_decode_with_definition_matches_decode_word():
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
    w.set_bit_field(30, 31, 0b10)
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
    w = Word()
    w.label = 0o203
    w.data = 100  # 100 feet at resolution 1.0

    decoded = w.decode_by_label(EQUIP_ADC)
    assert float(decoded["altitude"]) == 100.0


def test_decode_word_unknown_label_returns_none():
    w = Word()
    w.label = 0o777  # not in definitions
    result = decode_word(w, {})
    assert result is None


def test_validate_field_bcd_invalid_digits():
    field = FieldDefinition("bcd_val", 11, 23, "BCD", Decimal("1.0"))
    w = _word_with_field(field, 0x1A3)  # A is invalid BCD digit
    errors = validate_field(w, field)
    assert any("invalid BCD digits" in e for e in errors)


def test_validate_field_resolution_required_for_bnr_bcd():
    field_bnr = FieldDefinition("bnr_val", 11, 15, "BNR", None)
    field_bcd = FieldDefinition("bcd_val", 11, 23, "BCD", None)
    w = Word()
    errors_bnr = validate_field(w, field_bnr)
    errors_bcd = validate_field(w, field_bcd)
    assert any("missing resolution" in e for e in errors_bnr)
    assert any("missing resolution" in e for e in errors_bcd)


def test_validate_label_structure_overlap_and_duplicates():
    f1 = FieldDefinition("a", 11, 15, "BNR", Decimal("1.0"))
    f2 = FieldDefinition("b", 14, 20, "BNR", Decimal("1.0"))  # overlaps with a
    f3 = FieldDefinition("a", 21, 25, "BNR", Decimal("1.0"))  # duplicate name

    defn = LabelDefinition(name="Test", fields=(f1, f2, f3))
    errors = validate_label_structure(defn)
    assert any("overlap" in e for e in errors)
    assert any("Duplicate field names" in e for e in errors)


def test_validate_metadata_label_mismatch():
    from arinc429.labelinfo import LabelInfo

    info = LabelInfo(label=0o203, name="Alt", system="ADC", category="Air Data")
    w = Word()
    w.label = 0o210
    errors = validate_metadata(w, info)
    assert any("does not match" in e for e in errors)


def test_decode_field_negative_bnr_not_misread_as_bcd():
    field = FieldDefinition("signed", 11, 15, "BNR", Decimal("1.0"))
    w = _word_with_field(field, 0b11111)

    definition = LabelDefinition(name="Signed", fields=(field,))
    decoded = w.decode_with_definition(definition)
    assert float(decoded["signed"]) == -1.0


def test_generate_icd_code_emits_correct_signed_decode(tmp_path):
    from arinc429.icd import generate_icd_code

    icd = {
        "labels": [
            {
                "label": "0o203",
                "name": "Pressure Altitude",
                "system": "ADC",
                "category": "Air Data",
                "fields": [
                    {
                        "name": "Altitude",
                        "lsb": 11,
                        "msb": 29,
                        "type": "BNR",
                        "resolution": 1.0,
                    },
                    {
                        "name": "Status",
                        "lsb": 30,
                        "msb": 31,
                        "type": "DISCRETE",
                    },
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
    exec(src, ns)  # noqa: S102

    w = Word()
    w.label = 0o203
    w.set_bit_field(11, 29, 0x7FFFF)  # -1 in 19-bit two's complement
    w.set_bit_field(30, 31, 0b10)

    obj = ns["decode_icd_word"](w)
    assert obj is not None
    assert obj.altitude == -1.0
    assert int(obj.status) == 2
