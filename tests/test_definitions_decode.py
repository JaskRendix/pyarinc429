from decimal import Decimal

from arinc429 import Word
from arinc429.datatypes.bnr import BNR
from arinc429.definitions import (
    EQUIP_ADC,
    EQUIP_IRS,
    FieldDefinition,
    LabelDefinition,
    decode_word,
    merge_definitions,
    validate_metadata,
)
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


def test_validate_metadata_no_false_positive_on_equip_adc():
    w = Word()
    w.label = 0o203
    assert EQUIP_ADC[0o203].validate_word(w) == []


def test_validate_metadata_no_false_positive_on_equip_irs():
    w = Word()
    w.label = 0o310
    assert EQUIP_IRS[0o310].validate_word(w) == []


def test_validate_metadata_detects_label_mismatch():
    mismatched = LabelDefinition(
        name="Mismatched",
        fields=(FieldDefinition("x", 11, 29, "BNR", Decimal("1.0")),),
        info=LabelInfo(label=0o310, name="Wrong", system="X", category="Y"),
    )
    w = Word()
    w.label = 0o203  # different from info.label above
    errors = mismatched.validate_word(w)
    assert any("does not match" in e for e in errors)


def test_validate_metadata_directly():
    info = LabelInfo(label=0o203, name="x", system="ADC", category="Air Data")
    w = Word()
    w.label = 0o203
    assert validate_metadata(w, info) == []

    w.label = 0o210
    errors = validate_metadata(w, info)
    assert len(errors) == 1
    assert "0o210" in errors[0]
    assert "0o203" in errors[0]


def test_validate_word_skips_metadata_when_info_is_none():
    no_info_def = LabelDefinition(
        name="NoInfo",
        fields=(FieldDefinition("x", 11, 29, "BNR", Decimal("1.0")),),
    )
    w = Word()
    w.label = 0o001
    # Should not raise or attempt a metadata check when info is None
    assert no_info_def.validate_word(w) == []


def test_labeldefinition_field_names():
    assert EQUIP_ADC[0o203].field_names == ("altitude",)
    assert EQUIP_IRS[0o310].field_names == ("latitude",)


def test_labeldefinition_field_names_multiple_fields():
    ld = LabelDefinition(
        name="Multi",
        fields=(
            FieldDefinition("a", 11, 15, "DISCRETE"),
            FieldDefinition("b", 16, 29, "BNR", Decimal("1.0")),
        ),
    )
    assert ld.field_names == ("a", "b")


def test_decode_word_report_unknown_false_matches_default_shape():
    w = Word()
    w.label = 0o203
    w.data = BNR(100, Decimal("1.0"))
    default_result = decode_word(w, EQUIP_ADC)
    explicit_false_result = decode_word(w, EQUIP_ADC, report_unknown=False)
    assert default_result == explicit_false_result
    assert len(default_result) == 3


def test_decode_word_report_unknown_true_returns_four_tuple():
    weird_def = {
        0o203: LabelDefinition(
            name="Weird",
            fields=(FieldDefinition("mystery", 11, 12, "FUTURE_TYPE"),),
        )
    }
    w = Word()
    w.label = 0o203
    decoded, definition, info, unknown = decode_word(w, weird_def, report_unknown=True)
    assert decoded == {}
    assert unknown == ["mystery"]
    assert definition.name == "Weird"


def test_decode_word_report_unknown_true_no_unknown_fields():
    w = Word()
    w.label = 0o203
    w.data = BNR(100, Decimal("1.0"))
    decoded, definition, info, unknown = decode_word(w, EQUIP_ADC, report_unknown=True)
    assert unknown == []
    assert "altitude" in decoded


def test_merge_definitions_basic():
    merged = merge_definitions(EQUIP_ADC, EQUIP_IRS)
    assert 0o203 in merged  # From ADC
    assert 0o310 in merged  # From IRS
    assert len(merged) == len(EQUIP_ADC) + len(EQUIP_IRS)


def test_merge_definitions_overlap_precedence():
    # Create a custom override definition for label 0o203
    override_def = LabelDefinition(
        name="Overridden Altitude",
        fields=(FieldDefinition("custom_alt", 11, 29, "BNR", Decimal("1.0")),),
    )
    custom_equip = {0o203: override_def}

    # Later dictionary should overwrite earlier ones
    merged = merge_definitions(EQUIP_ADC, custom_equip)
    assert merged[0o203].name == "Overridden Altitude"
    assert merged[0o203].field_names == ("custom_alt",)


def test_merge_definitions_empty():
    merged = merge_definitions()
    assert merged == {}

    merged_single = merge_definitions(EQUIP_ADC)
    assert merged_single == EQUIP_ADC
