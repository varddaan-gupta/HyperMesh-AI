"""Purpose: load bundled satellite/debris data and validate satellite CSV imports.

Inputs: data JSON files, user-selected CSV paths, and an A/B assignment slot.
Outputs: validated satellite records, searchable catalog entries, and persisted
local imports in the per-user app-data directory.
Connection: dashboard consumes CSV records; the Satellite Data screen displays
bundled objects, imported records, and recent encounter analyses.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from engines.prediction_engine import validate_satellite

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

CSV_ALIASES = {
    "name": ("name", "satellite_name", "object", "object_name", "id"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng"),
    "altitude": ("altitude", "altitude_km", "alt_km"),
    "velocity": ("velocity", "velocity_kms", "speed", "speed_kms"),
    "inclination": ("inclination", "inclination_deg", "inc"),
}


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return value


def imported_catalog_path() -> Path:
    """Resolve the writable user-specific imported satellite catalog."""
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not location:
        raise OSError("The operating system did not provide an application data directory.")
    directory = Path(location)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "imported_satellites.json"


def read_satellite_csv(csv_path: str | Path) -> list[dict]:
    """Read one or more satellite rows from a CSV with common header aliases."""
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError("The CSV needs a header row with satellite fields.")
        headers = {header.strip().casefold(): header for header in reader.fieldnames if header}
        columns: dict[str, str] = {}
        for field, aliases in CSV_ALIASES.items():
            column = next((headers[alias] for alias in aliases if alias in headers), None)
            if column is None:
                expected = ", ".join(aliases)
                raise ValueError(f"CSV is missing '{field}'. Accepted header names: {expected}.")
            columns[field] = column

        satellites = []
        for line_number, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            satellite: dict = {"name": (row.get(columns["name"]) or "").strip()}
            for field in ("latitude", "longitude", "altitude", "velocity", "inclination"):
                try:
                    satellite[field] = float((row.get(columns[field]) or "").strip())
                except ValueError as exc:
                    raise ValueError(f"Row {line_number}: '{field}' must be a number.") from exc
            try:
                validate_satellite(satellite)
            except ValueError as exc:
                raise ValueError(f"Row {line_number}: {exc}") from exc
            satellites.append(satellite)
    if not satellites:
        raise ValueError("The selected CSV contains no satellite rows.")
    return satellites


def save_imported_satellites(satellites: list[dict]) -> None:
    """Append validated rows to the local catalog without altering bundled data."""
    path = imported_catalog_path()
    existing = _read_json(path).get("satellites", []) if path.exists() else []
    if not isinstance(existing, list):
        raise ValueError("The local imported satellite catalog has an invalid format.")
    existing.extend(satellites)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"satellites": existing}, indent=2), encoding="utf-8")
    temporary.replace(path)


def get_satellite_catalog() -> list[dict]:
    """Return bundled, locally imported, and debris objects for the data view."""
    bundled = _read_json(DATA_DIR / "satellites.json").get("satellites", [])
    debris = _read_json(DATA_DIR / "debris.json").get("debris_objects", [])
    path = imported_catalog_path()
    imported = _read_json(path).get("satellites", []) if path.exists() else []
    return [
        {**record, "category": "Satellite", "source": "Bundled catalog"}
        for record in bundled
    ] + [
        {**record, "category": "Satellite", "source": "CSV import"}
        for record in imported
    ] + [
        {
            "name": record["id"],
            "latitude": record["latitude"],
            "longitude": record["longitude"],
            "altitude": record["altitude"],
            "velocity": record["velocity"],
            "inclination": record["inclination"],
            "category": "Debris",
            "source": "Bundled catalog",
        }
        for record in debris
    ]


def get_recent_cases(limit: int = 8) -> list[dict]:
    """Return the latest local encounter records from knowledge.json."""
    cases = _read_json(DATA_DIR / "knowledge.json").get("cases", [])
    return sorted(cases, key=lambda case: case.get("created_at", ""), reverse=True)[:limit]
