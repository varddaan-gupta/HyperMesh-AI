"""Purpose: mission-control dashboard for entering and comparing two satellites.

Inputs: satellite orbital elements entered in the form.
Outputs: validated analysis, persisted local case, and navigation signals.
Connection: invokes prediction_engine and rag_engine, then shares a structured
result with the orbital tracking and report screens through main.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from engines.prediction_engine import predict_encounter
from engines.rag_engine import explain_encounter, record_encounter, retrieve_similar_cases
from screens.space_widget import SpaceWidget
from screens.theme import CYAN, MUTED, PRIMARY, make_panel

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class DashboardScreen(SpaceWidget):
    """Accepts orbital elements, runs local screening, and presents mission KPIs."""

    analysisReady = Signal(dict)
    openOrbit = Signal(dict)
    openReport = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.current_result: dict = {}
        self.fields: dict[str, dict[str, QLineEdit]] = {"a": {}, "b": {}}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(38, 32, 38, 34)
        root.setSpacing(22)
        header = QHBoxLayout()
        brand = QLabel("HYPERMESH <span style='color:#00AEEF'>AI</span>")
        brand.setTextFormat(Qt.TextFormat.RichText)
        brand.setStyleSheet("font-size: 23px; font-weight: 800; letter-spacing: 2px;")
        header.addWidget(brand)
        header.addStretch()
        header.addWidget(QLabel("ORBITAL INTELLIGENCE  /  MISSION CONTROL"))
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(18)
        inputs_panel, inputs_layout = make_panel("Conjunction Screening")
        intro = QLabel("Compare two orbital objects using a local geometry-based risk model.")
        intro.setStyleSheet(f"color: {MUTED};")
        inputs_layout.addWidget(intro)
        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(26)
        form_grid.addWidget(self._column_heading("SATELLITE A", "#00AEEF"), 0, 0)
        form_grid.addWidget(self._column_heading("SATELLITE B", "#00FFFF"), 0, 1)
        satellite_data = self._load_satellite_defaults()
        for col, key in enumerate(("a", "b")):
            form = QFormLayout()
            form.setVerticalSpacing(9)
            for name in ("name", "latitude", "longitude", "altitude", "velocity", "inclination"):
                edit = QLineEdit(str(satellite_data[col][name]))
                edit.setPlaceholderText(name.replace("_", " ").title())
                self.fields[key][name] = edit
                label = name.replace("_", " ").title()
                if name in ("latitude", "longitude", "inclination"):
                    label += " (°)"
                elif name == "altitude":
                    label += " (km)"
                elif name == "velocity":
                    label += " (km/s)"
                form.addRow(label, edit)
            form_widget = QWidget()
            form_widget.setLayout(form)
            form_grid.addWidget(form_widget, 1, col)
        inputs_layout.addLayout(form_grid)
        self.status = QLabel("READY FOR ORBITAL SCREENING")
        self.status.setStyleSheet(f"color: {CYAN}; font-size: 11px; letter-spacing: 1px;")
        inputs_layout.addWidget(self.status)
        self.analyze_button = QPushButton("RUN COLLISION ANALYSIS")
        self.analyze_button.clicked.connect(self.run_analysis)
        inputs_layout.addWidget(self.analyze_button)

        results_panel, results_layout = make_panel("Live Risk Overview")
        self.risk_label = QLabel("AWAITING ANALYSIS")
        self.risk_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.risk_label.setStyleSheet("font-size: 24px; font-weight: 800; color: #91A3BB; padding: 18px;")
        results_layout.addWidget(self.risk_label)
        self.metric_values: dict[str, QLabel] = {}
        metrics = QGridLayout()
        metric_titles = (
            ("Collision Probability", "probability"), ("Confidence Score", "confidence"),
            ("Closest Approach", "approach"), ("Relative Velocity", "velocity"),
        )
        for index, (title, key) in enumerate(metric_titles):
            card = QFrame()
            card.setStyleSheet("background: rgba(15,35,60,190); border: 1px solid #1D3D5A; border-radius: 10px;")
            card_layout = QVBoxLayout(card)
            label = QLabel(title.upper())
            label.setStyleSheet(f"color:{MUTED}; font-size:10px; border:none;")
            value = QLabel("--")
            value.setStyleSheet(f"font-size:22px; font-weight:700; color:{PRIMARY}; border:none;")
            self.metric_values[key] = value
            card_layout.addWidget(label)
            card_layout.addWidget(value)
            metrics.addWidget(card, index // 2, index % 2)
        results_layout.addLayout(metrics)
        self.explanation = QLabel("Run an analysis to see a transparent explanation and similar local cases.")
        self.explanation.setWordWrap(True)
        self.explanation.setStyleSheet(f"color:{MUTED}; padding:10px 2px;")
        results_layout.addWidget(self.explanation)
        actions = QHBoxLayout()
        self.orbit_button = QPushButton("VIEW ORBITAL TRACKING")
        self.orbit_button.setEnabled(False)
        self.orbit_button.clicked.connect(lambda: self.openOrbit.emit(self.current_result))
        self.report_button = QPushButton("MISSION REPORT")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(lambda: self.openReport.emit(self.current_result))
        actions.addWidget(self.orbit_button)
        actions.addWidget(self.report_button)
        results_layout.addLayout(actions)
        content.addWidget(inputs_panel, 5)
        content.addWidget(results_panel, 4)
        root.addLayout(content, 1)
        footer = QLabel("LOCAL MODEL  •  NO EXTERNAL LLM  •  SCREENING ESTIMATE, NOT FLIGHT GUIDANCE")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color:{MUTED}; font-size:10px; letter-spacing:1px;")
        root.addWidget(footer)

    @staticmethod
    def _load_satellite_defaults() -> list[dict]:
        """Read the two starter objects from data/satellites.json."""
        with (DATA_DIR / "satellites.json").open("r", encoding="utf-8") as file:
            data = json.load(file)
        satellites = data.get("satellites")
        if not isinstance(satellites, list) or len(satellites) < 2:
            raise ValueError(f"{DATA_DIR / 'satellites.json'} must contain at least two satellites.")
        return satellites[:2]

    @staticmethod
    def _column_heading(text: str, color: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color:{color}; font-weight:800; letter-spacing:1px; padding:4px 0;")
        return label

    def _read_satellite(self, key: str) -> dict:
        values = {name: field.text().strip() for name, field in self.fields[key].items()}
        if not values["name"]:
            raise ValueError("Satellite name cannot be empty.")
        record: dict[str, str | float] = {"name": values["name"]}
        for name in ("latitude", "longitude", "altitude", "velocity", "inclination"):
            try:
                record[name] = float(values[name])
            except ValueError as exc:
                raise ValueError(f"{name.replace('_', ' ').title()} must be a number for Satellite {key.upper()}.") from exc
        return record

    def set_satellite(self, key: str, satellite: dict) -> None:
        """Populate one A/B form with a validated record from the data catalog."""
        if key not in self.fields:
            raise ValueError(f"Unknown satellite assignment slot: {key}")
        values = {
            "name": satellite["name"],
            "latitude": satellite["latitude"],
            "longitude": satellite["longitude"],
            "altitude": satellite["altitude"],
            "velocity": satellite["velocity"],
            "inclination": satellite["inclination"],
        }
        for field, value in values.items():
            self.fields[key][field].setText(str(value))
        self.status.setText(f"SATELLITE {key.upper()} LOADED  •  {satellite['name']}")

    def run_analysis(self) -> None:
        """Validate form data, run prediction and retrieval, then update the dashboard."""
        self.analyze_button.setEnabled(False)
        try:
            satellite_a = self._read_satellite("a")
            satellite_b = self._read_satellite("b")
            result = predict_encounter(satellite_a, satellite_b)
            similar_cases = retrieve_similar_cases(result)
            explanation = explain_encounter(result, similar_cases)
            result["similar_cases"] = similar_cases
            result["explanation"] = explanation
            record_encounter(result, explanation, similar_cases)
            self.current_result = result
            self._show_result(result)
            self.analysisReady.emit(result)
        except (ValueError, OSError, TypeError) as exc:
            QMessageBox.warning(self, "Analysis could not be completed", str(exc))
            self.status.setText("CHECK INPUTS / LOCAL KNOWLEDGE FILE")
        finally:
            self.analyze_button.setEnabled(True)

    def _show_result(self, result: dict) -> None:
        risk = result["risk_level"]
        colors = {"LOW": "#40D98A", "MEDIUM": "#FFD166", "HIGH": "#FF9F43", "CRITICAL": "#FF4D6D"}
        self.risk_label.setText(f"{risk} RISK")
        self.risk_label.setStyleSheet(
            f"font-size:24px; font-weight:800; color:{colors[risk]}; padding:18px;"
        )
        self.metric_values["probability"].setText(f"{result['collision_probability']:.1%}")
        self.metric_values["confidence"].setText(f"{result['confidence']:.0%}")
        self.metric_values["approach"].setText(f"{result['closest_approach_km']:.1f} km")
        self.metric_values["velocity"].setText(f"{result['relative_velocity_kms']:.2f} km/s")
        self.explanation.setText(result["explanation"])
        self.status.setText("ANALYSIS COMPLETE  •  CASE STORED LOCALLY")
        self.orbit_button.setEnabled(True)
        self.report_button.setEnabled(True)
