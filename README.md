# HyperMesh AI

HyperMesh AI is a local-only PySide6 hackathon prototype for orbital encounter
screening, input-derived orbit visualization, historical-case retrieval, and
mission report export. It uses no Ollama service, external language model, or
network API.

## Run

```powershell
python -m pip install -r requirements.txt
python main.py
```

The app opens in a normal resizable desktop window with the Windows title bar
and taskbar available. On first launch, create a local operator account; later
launches ask for that username and password. Choose **ENTER PLATFORM** to open
the workspace. The left navigation remains visible while switching among
Mission Overview, Orbital Tracking, Mission Reports, and Satellite Data.

The overview compares two editable satellite records. The Satellite Data view
supports CSV imports (one or more rows) with these columns:
`name,latitude,longitude,altitude,velocity,inclination`. Common short aliases
such as `lat`, `lon`, `altitude_km`, `velocity_kms`, and `inclination_deg` are
also accepted. Imported records persist in the current Windows user's app-data
folder and can be loaded into either analysis slot. Mission reports can be
exported as PDF.

The local password is stored as a salted PBKDF2 hash and is only an application
access gate. It does not encrypt mission data files or protect the Windows
account. The intro voice asset is not played by the app, avoiding multimedia
codec initialization and diagnostics during startup.

Orbital Tracking plots inferred paths from the analyzed satellite records and
uses the provided logos for Satellite A and B. These are estimates based on
the available fields, not live tracking: the CSV format does not include full
ephemerides, covariance, or orbital orientation data such as ascending node.

## Project map

- `main.py` owns application startup and screen navigation.
- `screens/` contains the intro, authentication gate, dashboard, orbital
  tracking view, report, satellite catalog, and shared theme/background.
- `engines/orbit_engine.py` infers state vectors; `prediction_engine.py`
  performs deterministic encounter screening; `rag_engine.py` retrieves and
  stores similar local cases and generated reports; `data_engine.py` validates
  and manages CSV imports.
- `data/satellites.json` and `data/debris.json` contain prototype object records.
  `data/knowledge.json` stores historical cases, generated reports, and new
  locally-run scenarios.
- `assets/` contains the provided background, logos, and intro voice recording.

## Model scope

The prediction is an illustrative circular-orbit screening estimate with a
heuristic uncertainty envelope and confidence score. It is not a validated
collision probability, full orbital propagator, or flight-safety system.
Operational decisions require authoritative ephemerides, covariance data, and
review by qualified flight-dynamics personnel.
