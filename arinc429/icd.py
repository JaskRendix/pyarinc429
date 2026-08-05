from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arinc429.labelinfo import LabelInfo, LABEL_INFO


def load_icd_json(file_path: str | Path) -> dict[int, LabelInfo]:
    """
    Load custom ARINC 429 label metadata and definitions from an ICD JSON file.
    
    Expected JSON format:
    {
      "labels": [
        {
          "label": "0o203",
          "name": "Pressure Altitude",
          "system": "ADC",
          "category": "Air Data",
          "direction": "Source",
          "description": "Custom altitude description"
        }
      ]
    }
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ICD file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    loaded_info: dict[int, LabelInfo] = {}

    for item in data.get("labels", []):
        # Support octal strings (e.g., "0o203"), hex, or integers for labels
        raw_label = item["label"]
        label_int = int(raw_label, 0) if isinstance(raw_label, str) else int(raw_label)

        info = LabelInfo(
            label=label_int,
            name=item["name"],
            system=item["system"],
            category=item["category"],
            direction=item.get("direction"),
            description=item.get("description"),
        )
        loaded_info[label_int] = info
        # Optionally register globally or return for local use
        LABEL_INFO[label_int] = info

    return loaded_info


def generate_icd_code(file_path: str | Path) -> str:
    """
    Load an ICD JSON file and generate Python source code featuring:
      - typed dataclasses per label
      - field decoding based on ICD 'fields' definitions
      - a registry mapping label -> dataclass
      - helper decode function for ARINC 429 Word objects

    Expected ICD JSON structure:

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
              "unit": "ft"
            }
          ]
        }
      ]
    }
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ICD file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    lines: list[str] = [
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from typing import Any, Dict, Type, Optional",
        "",
        "from arinc429.word import Word",
        "from arinc429.datatypes.bnr import BNR",
        "from arinc429.datatypes.bcd import BCD",
        "from arinc429.datatypes.discrete import Discrete",
        "",
        "# Auto-generated from ICD JSON",
        "",
    ]

    registry_entries: list[str] = []
    class_names_by_label: dict[int, str] = {}

    def sanitize_class_name(name: str) -> str:
        # Turn arbitrary label names into safe Python identifiers
        base = "".join(ch if ch.isalnum() else " " for ch in name)
        parts = [p for p in base.split() if p]
        if not parts:
            parts = ["Label"]
        class_name = "".join(p.capitalize() for p in parts) + "Data"
        if class_name[0].isdigit():
            class_name = "_" + class_name
        return class_name

    def sanitize_field_name(name: str) -> str:
        base = "".join(ch if ch.isalnum() else "_" for ch in name)
        if not base:
            base = "field"
        if base[0].isdigit():
            base = "_" + base
        return base.lower()

    for item in data.get("labels", []):
        raw_label = item["label"]
        label_int = int(raw_label, 0) if isinstance(raw_label, str) else int(raw_label)

        name = item.get("name", f"Label_{label_int}")
        system = item.get("system", "UnknownSystem")
        category = item.get("category", "UnknownCategory")
        direction = item.get("direction", None)
        description = item.get("description", "")

        class_name = sanitize_class_name(name)
        class_names_by_label[label_int] = class_name

        # Docstring
        doc = f"{name} — {system} / {category}"
        if direction:
            doc += f" / {direction}"
        if description:
            doc += f" — {description}"

        lines.append(f"@dataclass")
        lines.append(f"class {class_name}:")
        lines.append(f'    """{doc}"""')

        # Base fields
        lines.append(f"    sdi: int")
        lines.append(f"    ssm: int")
        lines.append(f"    raw_data: int")

        # Field definitions from ICD
        fields = item.get("fields", [])
        for field in fields:
            fname = sanitize_field_name(field.get("name", "field"))
            ftype = field.get("type", "BNR").upper()

            # Choose Python type hint based on ICD type
            if ftype == "BNR":
                py_type = "float"
            elif ftype == "BCD":
                py_type = "int"
            elif ftype == "DISCRETE":
                py_type = "int"
            else:
                py_type = "Any"

            lines.append(f"    {fname}: {py_type}")

        lines.append("")
        lines.append(f"    @classmethod")
        lines.append(f"    def from_word(cls, word: Word) -> {class_name}:")
        lines.append(f"        \"\"\"Decode an ARINC 429 Word into {class_name} using ICD field definitions.\"\"\"")
        lines.append(f"        sdi = word.sdi")
        lines.append(f"        ssm = word.ssm")
        lines.append(f"        raw_data = word.data")

        # Decode fields
        if fields:
            lines.append(f"        # Decode fields from ICD")
            for field in fields:
                fname = sanitize_field_name(field.get("name", "field"))
                lsb = field.get("lsb")
                msb = field.get("msb")
                ftype = field.get("type", "BNR").upper()
                resolution = field.get("resolution", None)

                lines.append(f"        # Field: {field.get('name', fname)} [{ftype}] bits {lsb}..{msb}")
                lines.append(f"        bits_{fname} = word.get_bit_field({lsb}, {msb})")

                if ftype == "BNR":
                    # Use BNR.decode so two's-complement sign extension is
                    # applied for negative values (BNR(value) is an encoder).
                    width = int(msb) - int(lsb) + 1
                    if resolution is None:
                        lines.append(f"        {fname} = float(BNR.decode(bits_{fname}, {width}).decoded)")
                    else:
                        lines.append(f"        {fname} = float(BNR.decode(bits_{fname}, {width}, resolution={resolution}).decoded)")
                elif ftype == "BCD":
                    # SSM carries the sign/status for BCD data on ARINC 429.
                    if resolution is None:
                        lines.append(f"        {fname} = int(BCD.decode(bits_{fname}, ssm).decoded)")
                    else:
                        lines.append(f"        {fname} = int(BCD.decode(bits_{fname}, ssm, resolution={resolution}).decoded)")
                elif ftype == "DISCRETE":
                    lines.append(f"        {fname} = int(Discrete(bits_{fname}).decoded)")
                else:
                    lines.append(f"        {fname} = bits_{fname}  # Unknown type, raw bits")

            # Return with decoded fields
            field_args = ", ".join(
                [f"{sanitize_field_name(f.get('name', 'field'))}={sanitize_field_name(f.get('name', 'field'))}"
                 for f in fields]
            )
            lines.append(f"        return cls(sdi=sdi, ssm=ssm, raw_data=raw_data, {field_args})")
        else:
            # No fields defined, just wrap raw data
            lines.append(f"        return cls(sdi=sdi, ssm=ssm, raw_data=raw_data)")
        lines.append("")

        # Registry entry
        registry_entries.append(f"    {label_int}: {class_name},")

    # Registry and helper
    lines.append("ICD_REGISTRY: Dict[int, Type[Any]] = {")
    for entry in registry_entries:
        lines.append(entry)
    lines.append("}")
    lines.append("")
    lines.append("def decode_icd_word(word: Word) -> Optional[Any]:")
    lines.append("    \"\"\"Lookup ICD dataclass for the given word.label and decode it, if available.\"\"\"")
    lines.append("    cls = ICD_REGISTRY.get(word.label)")
    lines.append("    if cls is None:")
    lines.append("        return None")
    lines.append("    return cls.from_word(word)")
    lines.append("")

    return "\n".join(lines)
