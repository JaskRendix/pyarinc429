import dataclasses
from decimal import Decimal

import pytest

from arinc429.definitions import EQUIP_ADC, EQUIP_IRS, FieldDefinition, LabelDefinition
from arinc429.word import Word


def test_labeldefinition_basic_fields():
    ld = LabelDefinition(
        name="Test Label",
        fields=(
            FieldDefinition(
                name="f",
                lsb=11,
                msb=29,
                type="BNR",
                resolution=Decimal("0.5"),
                unit="Meters",
            ),
        ),
    )

    assert ld.name == "Test Label"
    assert len(ld.fields) == 1

    f = ld.fields[0]
    assert f.name == "f"
    assert f.type == "BNR"
    assert f.resolution == Decimal("0.5")
    assert f.unit == "Meters"


def test_labeldefinition_is_frozen():
    ld = LabelDefinition(
        name="Immutable",
        fields=(
            FieldDefinition(
                name="x",
                lsb=11,
                msb=29,
                type="DISCRETE",
            ),
        ),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        ld.name = "Changed"


@pytest.mark.parametrize("dtype", ["BNR", "BCD", "DISCRETE"])
def test_fielddefinition_accepts_valid_types(dtype):
    f = FieldDefinition("x", 11, 29, dtype, Decimal("1"))
    assert f.type == dtype


def test_fielddefinition_resolution_is_decimal():
    f = FieldDefinition("x", 11, 29, "BNR", Decimal("0.1"))
    assert isinstance(f.resolution, Decimal)


def test_fielddefinition_width():
    f = FieldDefinition("x", 11, 29, "BNR")
    assert f.width == 19


def test_equip_adc_contains_expected_labels():
    assert 0o203 in EQUIP_ADC
    assert 0o210 in EQUIP_ADC

    ld = EQUIP_ADC[0o203]
    assert ld.name == "Pressure Altitude"
    assert len(ld.fields) == 1

    f = ld.fields[0]
    assert f.type == "BNR"
    assert f.unit == "Feet"


def test_equip_irs_contains_expected_labels():
    assert 0o310 in EQUIP_IRS
    assert 0o311 in EQUIP_IRS

    ld = EQUIP_IRS[0o310]
    f = ld.fields[0]
    assert f.resolution == Decimal("0.0001")


def test_labeldefinition_objects_are_immutable():
    ld = EQUIP_ADC[0o203]
    with pytest.raises(Exception):
        ld.fields = ()


def test_equip_dicts_are_mutable_but_values_are_not():
    EQUIP_ADC[0o777] = LabelDefinition(
        name="Test",
        fields=(FieldDefinition("x", 11, 29, "BNR", Decimal("1")),),
    )
    assert 0o777 in EQUIP_ADC

    with pytest.raises(Exception):
        EQUIP_ADC[0o203].name = "Changed"

def test_labeldefinition_instance_decode_method():
    w = Word()
    w.label = 0o203
    w.data = BNR(250, Decimal("1.0"))

    ld = EQUIP_ADC[0o203]
    result = ld.decode(w)
    assert result is not None

    decoded_fields, definition, info = result
    assert definition.name == "Pressure Altitude"
    assert "altitude" in decoded_fields
    assert float(decoded_fields["altitude"]) == 250.0
