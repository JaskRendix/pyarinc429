import dataclasses
from decimal import Decimal

import pytest

from arinc429.definitions import EQUIP_ADC, EQUIP_IRS, LabelDefinition


def test_labeldefinition_basic_fields():
    ld = LabelDefinition(
        name="Test Label",
        type="BNR",
        resolution=Decimal("0.5"),
        unit="Meters",
    )

    assert ld.name == "Test Label"
    assert ld.type == "BNR"
    assert ld.resolution == Decimal("0.5")
    assert ld.unit == "Meters"


def test_labeldefinition_unit_optional():
    ld = LabelDefinition(
        name="No Unit",
        type="BCD",
        resolution=Decimal("1.0"),
        unit=None,
    )

    assert ld.unit is None


def test_labeldefinition_is_frozen():
    ld = LabelDefinition(
        name="Immutable",
        type="DISCRETE",
        resolution=Decimal("1"),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        ld.name = "Changed"


def test_labeldefinition_accepts_valid_types():
    for t in ["BNR", "BCD", "DISCRETE"]:
        ld = LabelDefinition("X", t, Decimal("1"))
        assert ld.type == t


def test_labeldefinition_resolution_must_be_decimal():
    ld = LabelDefinition("Test", "BNR", Decimal("0.1"))
    assert isinstance(ld.resolution, Decimal)


def test_labeldefinition_resolution_from_string():
    ld = LabelDefinition("Test", "BNR", Decimal("0.0001"))
    assert ld.resolution == Decimal("0.0001")


def test_equip_adc_contains_expected_labels():
    assert 0o203 in EQUIP_ADC
    assert 0o210 in EQUIP_ADC

    altitude = EQUIP_ADC[0o203]
    assert altitude.name == "Pressure Altitude"
    assert altitude.type == "BNR"
    assert altitude.unit == "Feet"


def test_equip_irs_contains_expected_labels():
    assert 0o310 in EQUIP_IRS
    assert 0o311 in EQUIP_IRS

    lat = EQUIP_IRS[0o310]
    assert lat.name == "Present Latitude"
    assert lat.resolution == Decimal("0.0001")


def test_labeldefinition_objects_are_immutable():
    ld = EQUIP_ADC[0o203]
    with pytest.raises(Exception):
        ld.unit = "Meters"


def test_equip_dicts_are_mutable_but_values_are_not():
    # You *can* add new entries
    EQUIP_ADC[0o777] = LabelDefinition("Test", "BNR", Decimal("1"))
    assert 0o777 in EQUIP_ADC

    # But the objects themselves remain frozen
    with pytest.raises(Exception):
        EQUIP_ADC[0o203].name = "Changed"
