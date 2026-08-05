from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from arinc429.icd import generate_icd_code, load_icd_json
from arinc429.labelinfo import LABEL_INFO, LabelInfo
from arinc429.word import Word


@pytest.mark.parametrize("label_value", ["0o203", "0x45", 123])
def test_load_icd_json_basic(tmp_path, label_value):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "label": label_value,
                        "name": "Pressure Altitude",
                        "system": "ADC",
                        "category": "Air Data",
                        "direction": "Source",
                        "description": "Test description",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    loaded = load_icd_json(icd_file)
    assert isinstance(loaded, dict)
    assert len(loaded) == 1

    raw = label_value
    label_int = int(raw, 0) if isinstance(raw, str) else int(raw)
    assert label_int in loaded

    info = loaded[label_int]
    assert isinstance(info, LabelInfo)
    assert info.label == label_int
    assert info.name == "Pressure Altitude"
    assert info.system == "ADC"
    assert info.category == "Air Data"
    assert info.direction == "Source"
    assert info.description == "Test description"

    assert LABEL_INFO[label_int] is info


def test_load_icd_json_file_not_found(tmp_path):
    missing = tmp_path / "no_such_icd.json"
    with pytest.raises(FileNotFoundError):
        load_icd_json(missing)


def test_load_icd_json_empty_labels(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(json.dumps({"labels": []}), encoding="utf-8")

    loaded = load_icd_json(icd_file)
    assert loaded == {}


def test_generate_icd_code_basic_bnr(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "label": "0o203",
                        "name": "Pressure Altitude",
                        "system": "ADC",
                        "category": "Air Data",
                        "direction": "Source",
                        "description": "Pressure altitude in feet",
                        "fields": [
                            {
                                "name": "Altitude",
                                "lsb": 11,
                                "msb": 28,
                                "type": "BNR",
                                "resolution": 1.0,
                                "unit": "ft",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    src = generate_icd_code(icd_file)
    assert "PressureAltitudeData" in src
    assert "ICD_REGISTRY" in src
    assert "decode_icd_word" in src
    assert "Altitude" in src

    module = types.ModuleType("generated_icd")
    module.__dict__["__name__"] = "generated_icd"
    sys.modules["generated_icd"] = module
    try:
        exec(src, module.__dict__)
    finally:
        sys.modules.pop("generated_icd", None)

    label_int = int("0o203", 0)
    assert hasattr(module, "ICD_REGISTRY")
    assert label_int in module.ICD_REGISTRY

    cls = module.ICD_REGISTRY[label_int]
    assert cls.__name__ == "PressureAltitudeData"

    w = Word()
    w.label = label_int
    w.sdi = 1
    w.ssm = 2
    w.data = 0x1234

    decoded = module.decode_icd_word(w)
    assert decoded is not None
    assert decoded.sdi == 1
    assert decoded.ssm == 2
    assert decoded.raw_data == w.data
    assert hasattr(decoded, "altitude")


def test_generate_icd_code_no_fields(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "label": 123,
                        "name": "Generic Label",
                        "system": "SYS",
                        "category": "Cat",
                        "description": "No fields here",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    src = generate_icd_code(icd_file)
    module = types.ModuleType("generated_icd_no_fields")
    module.__dict__["__name__"] = "generated_icd_no_fields"
    sys.modules["generated_icd_no_fields"] = module
    try:
        exec(src, module.__dict__)
    finally:
        sys.modules.pop("generated_icd_no_fields", None)

    label_int = 123
    assert label_int in module.ICD_REGISTRY
    cls = module.ICD_REGISTRY[label_int]

    w = Word()
    w.label = label_int
    w.sdi = 0
    w.ssm = 0
    w.data = 0x0

    decoded = module.decode_icd_word(w)
    assert decoded is not None
    assert decoded.sdi == 0
    assert decoded.ssm == 0
    assert decoded.raw_data == 0x0


def test_generate_icd_code_mixed_types(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "label": "0x45",
                        "name": "Mixed Types",
                        "system": "SYS",
                        "category": "Cat",
                        "fields": [
                            {
                                "name": "BnField",
                                "lsb": 11,
                                "msb": 20,
                                "type": "BNR",
                                "resolution": 0.5,
                            },
                            {"name": "BcField", "lsb": 21, "msb": 24, "type": "BCD"},
                            {
                                "name": "DiscField",
                                "lsb": 25,
                                "msb": 26,
                                "type": "DISCRETE",
                            },
                            {
                                "name": "RawField",
                                "lsb": 27,
                                "msb": 28,
                                "type": "UNKNOWN",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    src = generate_icd_code(icd_file)
    module = types.ModuleType("generated_icd_mixed")
    module.__dict__["__name__"] = "generated_icd_mixed"
    sys.modules["generated_icd_mixed"] = module
    try:
        exec(src, module.__dict__)
    finally:
        sys.modules.pop("generated_icd_mixed", None)

    label_int = int("0x45", 0)
    cls = module.ICD_REGISTRY[label_int]

    w = Word()
    w.label = label_int
    w.sdi = 3
    w.ssm = 1
    w.data = 0x12345

    decoded = module.decode_icd_word(w)
    assert decoded is not None
    assert decoded.sdi == 3
    assert decoded.ssm == 1
    assert decoded.raw_data == w.data

    assert hasattr(decoded, "bnfield")
    assert hasattr(decoded, "bcfield")
    assert hasattr(decoded, "discfield")
    assert hasattr(decoded, "rawfield")
