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
