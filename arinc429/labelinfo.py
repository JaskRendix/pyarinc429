from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelInfo:
    """
    Metadata describing an ARINC 429 label.

    This is intentionally minimal but extensible:
    - name: human-readable label name
    - system: subsystem or equipment class (ADC, IRS, FMS, GPS, etc.)
    - category: functional grouping (Air Data, Navigation, Attitude, etc.)
    - direction: optional (Source, Sink, Bidirectional)
    - description: optional free text
    """

    label: int
    name: str
    system: str
    category: str
    direction: str | None = None
    description: str | None = None


LABEL_INFO: dict[int, LabelInfo] = {
    # --- Air Data Computer (ADC) -------------------------------------------------
    0o203: LabelInfo(
        label=0o203,
        name="Pressure Altitude",
        system="ADC",
        category="Air Data",
        direction="Source",
        description="Altitude above mean sea level from the Air Data Computer.",
    ),
    0o210: LabelInfo(
        label=0o210,
        name="Indicated Airspeed",
        system="ADC",
        category="Air Data",
        direction="Source",
        description="Calibrated airspeed derived from pitot-static system.",
    ),
    # --- Inertial Reference System (IRS) ----------------------------------------
    0o310: LabelInfo(
        label=0o310,
        name="Present Latitude",
        system="IRS",
        category="Navigation",
        direction="Source",
        description="Aircraft latitude from inertial navigation solution.",
    ),
    0o311: LabelInfo(
        label=0o311,
        name="Present Longitude",
        system="IRS",
        category="Navigation",
        direction="Source",
        description="Aircraft longitude from inertial navigation solution.",
    ),
}


def get_label_info(label: int) -> LabelInfo | None:
    """
    Return LabelInfo for a given ARINC 429 label, or None if unknown.
    """
    return LABEL_INFO.get(label)


def require_label_info(label: int) -> LabelInfo:
    """
    Return LabelInfo for a given label, raising KeyError if not present.
    """
    info = get_label_info(label)
    if info is None:
        raise KeyError(f"No metadata available for ARINC 429 label {label:#o}")
    return info


def get_labels_by_system(system: str) -> list[LabelInfo]:
    """Return all label metadata registered for a specific system (e.g., 'ADC')."""
    return [
        info for info in LABEL_INFO.values() if info.system.upper() == system.upper()
    ]
