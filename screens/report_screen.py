"""Purpose: render a structured mission report and export it as a PDF.

Inputs: encounter result and locally retrieved similar-case records.
Outputs: readable report view, a persisted report record, and user-selected PDF.
Connection: receives dashboard analysis through main.py and is opened through
the persistent navigation rail.
"""

from __future__ import annotations

from html import escape
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout

from engines.rag_engine import record_report
from screens.space_widget import SpaceWidget


class ReportScreen(SpaceWidget):
    """Displays mission findings and exports the same content to PDF."""

    def __init__(self) -> None:
        super().__init__()
        self.analysis: dict = {}
        self._recorded_analysis_id: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(38, 30, 38, 32)
        header = QHBoxLayout()
        title = QLabel("MISSION INTELLIGENCE REPORT")
        title.setStyleSheet("font-size:22px; font-weight:800; letter-spacing:1px;")
        header.addWidget(title)
        header.addStretch()
        self.export_button = QPushButton("EXPORT PDF")
        self.export_button.clicked.connect(self.export_pdf)
        header.addWidget(self.export_button)
        root.addLayout(header)
        self.document = QTextBrowser()
        self.document.setOpenExternalLinks(False)
        root.addWidget(self.document, 1)

    def set_analysis(self, analysis: dict) -> None:
        self.analysis = analysis
        self.document.setHtml(self._make_html(analysis))
        if self._recorded_analysis_id != id(analysis):
            record_report(analysis, self._plain_text(analysis))
            self._recorded_analysis_id = id(analysis)

    @staticmethod
    def _plain_text(analysis: dict) -> str:
        satellites = analysis["satellites"]
        return (
            f"HyperMesh AI Mission Summary — {satellites['a']['name']} / {satellites['b']['name']}\n"
            f"Risk: {analysis['risk_level']}; collision probability: {analysis['collision_probability']:.1%}; "
            f"confidence: {analysis['confidence']:.0%}; closest approach: "
            f"{analysis['closest_approach_km']:.2f} km. Suggested action: {analysis['suggested_action']} "
            f"Explanation: {analysis.get('explanation', '')}"
        )

    def _make_html(self, data: dict) -> str:
        sat_a, sat_b = data["satellites"]["a"], data["satellites"]["b"]
        cases = data.get("similar_cases", [])
        case_list = "".join(
            f"<li><b>{escape(str(case.get('id', 'Historical case')))}</b> — "
            f"{escape(str(case.get('risk_level', 'Unknown')))} · "
            f"{escape(str(case.get('summary', '')))} "
            f"<span style='color:#91A3BB'>({case.get('similarity', 0):.0%} match)</span></li>"
            for case in cases
        ) or "<li>No similar cases are available in the local knowledge base.</li>"
        point = data["collision_point"]
        return f"""
        <html><body style="font-family:'Segoe UI'; color:#F4F8FF; background:#071122; line-height:1.55">
          <h1 style="color:#00AEEF">HYPERMESH AI <span style="color:#00FFFF">/ MISSION REPORT</span></h1>
          <p style="color:#91A3BB">LOCAL ORBITAL SCREENING · {escape(sat_a['name'])} / {escape(sat_b['name'])}</p>
          <hr style="border:1px solid #24415F">
          <h2>Mission Summary</h2>
          <p>Encounter screening for <b>{escape(sat_a['name'])}</b> and <b>{escape(sat_b['name'])}</b>
          estimates <b>{data['risk_level']}</b> risk within a 24-hour analysis window.</p>
          <table width="100%" cellspacing="10"><tr>
            <td><b>Collision probability</b><br><span style="font-size:20px;color:#00FFFF">{data['collision_probability']:.2%}</span></td>
            <td><b>Confidence score</b><br><span style="font-size:20px;color:#00FFFF">{data['confidence']:.0%}</span></td>
            <td><b>Closest approach</b><br><span style="font-size:20px;color:#00FFFF">{data['closest_approach_km']:.2f} km</span></td>
          </tr></table>
          <h2>Encounter Geometry</h2>
          <p>Relative velocity: <b>{data['relative_velocity_kms']:.2f} km/s</b><br>
          Time to closest approach: <b>{data['time_to_closest_hours']:.2f} hours</b><br>
          Predicted close point: <b>{point['latitude']:.2f}°, {point['longitude']:.2f}°</b>,
          altitude {point['altitude']:.1f} km.</p>
          <h2>Suggested Action</h2><p>{escape(data['suggested_action'])}</p>
          <h2>Explanation</h2><p>{escape(data.get('explanation', ''))}</p>
          <h2>Retrieved Similar Cases</h2><ul>{case_list}</ul>
          <hr style="border:1px solid #24415F">
          <p style="color:#91A3BB;font-size:10px">Prototype screening only. Simplified circular-orbit propagation and heuristic
          confidence are not operational flight guidance. Confirm conjunctions using authoritative tracking and covariance data.</p>
        </body></html>
        """

    def export_pdf(self) -> None:
        """Write the displayed report as a PDF at the path selected by the user."""
        if not self.analysis:
            QMessageBox.information(self, "No report", "Run a mission analysis before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Mission Report", "HyperMesh_Mission_Report.pdf", "PDF files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        document = QTextDocument()
        document.setHtml(self._make_html(self.analysis))
        try:
            document.print_(printer)
        except (OSError, RuntimeError) as exc:
            QMessageBox.critical(self, "PDF export failed", str(exc))
            return
        QMessageBox.information(self, "Report exported", f"Mission report saved to:\n{path}")
