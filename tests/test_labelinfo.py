import pytest

from arinc429.labelinfo import LABEL_INFO, LabelInfo, get_label_info, require_label_info


def test_labelinfo_structure():
    info = LABEL_INFO[0o203]
    assert isinstance(info, LabelInfo)
    assert info.label == 0o203
    assert info.name == "Pressure Altitude"
    assert info.system == "ADC"
    assert info.category == "Air Data"
    assert info.direction == "Source"
    assert info.description == "Test description"


def test_get_label_info_known():
    info = get_label_info(0o210)
    assert info is not None
    assert info.name == "Indicated Airspeed"


def test_get_label_info_unknown():
    assert get_label_info(0o777) is None
    assert get_label_info(-1) is None


def test_require_label_info_known():
    info = require_label_info(0o310)
    assert info.system == "IRS"
    assert info.category == "Navigation"


def test_require_label_info_unknown_raises():
    with pytest.raises(KeyError):
        require_label_info(0o777)


def test_labelinfo_is_frozen():
    info = LABEL_INFO[0o203]
    with pytest.raises(Exception):
        info.name = "New Name"  # frozen dataclass must reject mutation


def test_registry_contains_expected_labels():
    # Ensure core labels exist
    for lbl in (0o203, 0o210, 0o310, 0o311):
        assert lbl in LABEL_INFO


def test_registry_metadata_is_consistent():
    for lbl, info in LABEL_INFO.items():
        assert info.label == lbl
        assert isinstance(info.name, str)
        assert isinstance(info.system, str)
        assert isinstance(info.category, str)
