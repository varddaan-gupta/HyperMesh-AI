"""Purpose: catalog view, CSV import, and latest local encounter activity.

Inputs: bundled satellite/debris records, imported CSV files, and stored cases.
Outputs: a searchable object list, persistent validated imports, and A/B
satellite selection signals that populate the analysis form.
Connection: main.py connects selected objects to DashboardScreen and refreshes
this page after imports.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from engines.data_engine import get_recent_cases, get_satellite_catalog, read_satellite_csv, save_imported_satellites
from screens.space_widget import SpaceWidget
from screens.theme import MUTED, make_panel


class SatelliteDataScreen(SpaceWidget):
    """Browse object data, import satellite CSV files, and assign A/B inputs."""

    satelliteSelected = Signal(str, dict)

    def __init__(self) -> None:
        super().__init__()
        self._catalog: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 28)
        heading = QLabel("SATELLITE DATA")
        heading.setStyleSheet("font-size:25px; font-weight:800; letter-spacing:1px;")
        description = QLabel("Browse built-in objects, import mission CSV data, and load records directly into analysis.")
        description.setStyleSheet(f"color:{MUTED}; font-size:14px;")
        root.addWidget(heading)
        root.addWidget(description)
        actions = QHBoxLayout()
        import_a = QPushButton("IMPORT CSV → SATELLITE A")
        import_a.clicked.connect(lambda: self.import_csv("a"))
        import_b = QPushButton("IMPORT CSV → SATELLITE B")
        import_b.clicked.connect(lambda: self.import_csv("b"))
        refresh = QPushButton("REFRESH CATALOG")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(import_a)
        actions.addWidget(import_b)
        actions.addStretch()
        actions.addWidget(refresh)
        root.addLayout(actions)

        catalog_panel, catalog_layout = make_panel("Orbital Object Catalog")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Name / ID", "Type", "Altitude", "Latitude", "Longitude", "Velocity", "Source"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter satellites, debris, or data source…")
        self.search.textChanged.connect(self._filter_rows)
        catalog_layout.addWidget(self.search)
        catalog_layout.addWidget(self.table)
        selection_actions = QHBoxLayout()
        self.assign_a = QPushButton("LOAD SELECTED AS A")
        self.assign_a.clicked.connect(lambda: self.assign_selected("a"))
        self.assign_b = QPushButton("LOAD SELECTED AS B")
        self.assign_b.clicked.connect(lambda: self.assign_selected("b"))
        selection_actions.addWidget(self.assign_a)
        selection_actions.addWidget(self.assign_b)
        selection_actions.addStretch()
        catalog_layout.addLayout(selection_actions)
        root.addWidget(catalog_panel, 4)

        activity_panel, activity_layout = make_panel("Recent Encounter Cases")
        self.activity = QLabel("")
        self.activity.setWordWrap(True)
        self.activity.setStyleSheet(f"color:{MUTED}; line-height:1.5;")
        activity_layout.addWidget(self.activity)
        root.addWidget(activity_panel, 1)

    def refresh(self) -> None:
        """Reload persisted objects and recent cases into the visible widgets."""
        try:
            self._catalog = get_satellite_catalog()
            self.table.setRowCount(len(self._catalog))
            for row, item in enumerate(self._catalog):
                values = (
                    item["name"], item["category"], f"{float(item['altitude']):.1f} km",
                    f"{float(item['latitude']):.2f}°", f"{float(item['longitude']):.2f}°",
                    f"{float(item['velocity']):.2f} km/s", item["source"],
                )
                for column, value in enumerate(values):
                    self.table.setItem(row, column, QTableWidgetItem(str(value)))
            self.table.resizeColumnsToContents()
            self._filter_rows(self.search.text())
            cases = get_recent_cases()
            self.activity.setText(
                "\n".join(
                    f"• {case.get('created_at', 'Local')}  |  {case.get('risk_level', 'UNKNOWN')}  |  {case.get('id', 'Case')}"
                    for case in cases
                ) or "No local encounter history yet. Run an analysis to create the first case."
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "Catalog unavailable", str(exc))

    def _filter_rows(self, text: str) -> None:
        """Filter catalog rows by the visible object metadata."""
        query = text.casefold().strip()
        for row in range(self.table.rowCount()):
            visible = False
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None and query in item.text().casefold():
                    visible = True
                    break
            self.table.setRowHidden(row, bool(query) and not visible)

    def import_csv(self, slot: str) -> None:
        """Import all valid CSV rows, then assign the first row to A or B."""
        path, _ = QFileDialog.getOpenFileName(self, "Import satellite CSV", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            satellites = read_satellite_csv(path)
            save_imported_satellites(satellites)
            self.satelliteSelected.emit(slot, satellites[0])
            self.refresh()
            QMessageBox.information(
                self, "Satellite data imported",
                f"Imported {len(satellites)} satellite record(s). "
                f"The first row was loaded as Satellite {slot.upper()}.",
            )
        except (OSError, ValueError, UnicodeError) as exc:
            QMessageBox.warning(self, "CSV import failed", str(exc))

    def assign_selected(self, slot: str) -> None:
        """Load a selected satellite row into the matching analysis slot."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._catalog):
            QMessageBox.information(self, "Select a satellite", "Choose a satellite row first.")
            return
        selected = self._catalog[row]
        if selected["category"] != "Satellite":
            QMessageBox.information(self, "Debris record", "Debris rows are available for awareness; select a satellite record for A/B input.")
            return
        satellite = {field: selected[field] for field in ("name", "latitude", "longitude", "altitude", "velocity", "inclination")}
        self.satelliteSelected.emit(slot, satellite)
        QMessageBox.information(self, "Satellite loaded", f"{selected['name']} loaded as Satellite {slot.upper()}.")
