"""Purpose: start the desktop app and coordinate its persistent navigation shell.

Inputs: OS-provided local operator credentials and bundled app assets/data.
Outputs: a normal, resizable desktop window with an intro and navigation shell.
Connection: hosts each screen once and routes analysis, satellite selection,
orbital data, reports, and sign-in events between them.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from screens.auth_dialog import AuthDialog
from screens.dashboard_screen import DashboardScreen
from screens.intro_screen import IntroScreen
from screens.report_screen import ReportScreen
from screens.satellite_data_screen import SatelliteDataScreen
from screens.orbit_screen import OrbitScreen
from screens.theme import CYAN, MUTED, apply_theme

ASSET_DIR = Path(__file__).resolve().parent / "assets"


class WorkspaceShell(QWidget):
    """Provide persistent app navigation, operator status, and a live clock."""

    def __init__(self, operator_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._pages: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, QPushButton] = {}
        self._build_ui(operator_name)
        self._connect_screens()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_clock)
        self._timer.start()
        self._update_clock()

    def _build_ui(self, operator_name: str) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 20)
        outer.setSpacing(18)

        sidebar = QFrame()
        sidebar.setObjectName("navigationRail")
        sidebar.setFixedWidth(245)
        sidebar.setStyleSheet(
            "#navigationRail { background:rgba(5,12,26,238); border:1px solid #1B3855; border-radius:18px; }"
        )
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(17, 18, 17, 18)
        side_layout.setSpacing(8)

        logo = QLabel()
        pixmap = QPixmap(str(ASSET_DIR / "logo.png"))
        logo.setPixmap(
            pixmap.scaled(
                88, 88, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("background:transparent;")
        side_layout.addWidget(logo)
        brand = QLabel("HYPERMESH <span style='color:#00AEEF'>AI</span>")
        brand.setTextFormat(Qt.TextFormat.RichText)
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("font-size:19px; font-weight:800; letter-spacing:1px; background:transparent;")
        side_layout.addWidget(brand)
        tagline = QLabel("SAFER ORBITS. SMARTER MISSIONS.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet(f"font-size:9px; color:{MUTED}; letter-spacing:1px; background:transparent;")
        side_layout.addWidget(tagline)
        side_layout.addSpacing(20)

        nav_items = (
            ("overview", "◈   MISSION OVERVIEW"),
            ("orbit", "◎   ORBITAL TRACKING"),
            ("reports", "▤   MISSION REPORTS"),
            ("data", "◉   SATELLITE DATA"),
        )
        for key, text in nav_items:
            button = QPushButton(text)
            button.setMinimumHeight(48)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, page=key: self._navigation_clicked(page, checked)
            )
            self._nav_buttons[key] = button
            side_layout.addWidget(button)
        side_layout.addStretch(1)

        operator_card = QFrame()
        operator_card.setStyleSheet(
            "background:rgba(12,31,53,200); border:1px solid #24415F; border-radius:12px;"
        )
        operator_layout = QVBoxLayout(operator_card)
        operator_title = QLabel("LOCAL OPERATOR")
        operator_title.setStyleSheet(f"color:{MUTED}; font-size:9px; letter-spacing:1px; border:none;")
        operator_value = QLabel(operator_name)
        operator_value.setStyleSheet("font-size:14px; font-weight:700; border:none;")
        operator_layout.addWidget(operator_title)
        operator_layout.addWidget(operator_value)
        side_layout.addWidget(operator_card)
        self.lock_button = QPushButton("LOCK WORKSPACE")
        self.lock_button.setStyleSheet("background:#14263B; border-color:#33516E;")
        side_layout.addWidget(self.lock_button)
        outer.addWidget(sidebar)

        right = QVBoxLayout()
        right.setSpacing(14)
        topbar = QFrame()
        topbar.setStyleSheet(
            "background:rgba(5,12,26,228); border:1px solid #1B3855; border-radius:15px;"
        )
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(22, 12, 22, 12)
        welcome = QLabel("ORBITAL INTELLIGENCE  /  MISSION CONTROL")
        welcome.setStyleSheet("font-size:12px; font-weight:700; letter-spacing:1px; border:none;")
        top_layout.addWidget(welcome)
        top_layout.addStretch()
        online = QLabel("●  LOCAL SYSTEM READY")
        online.setStyleSheet(f"font-size:10px; color:{CYAN}; border:none;")
        top_layout.addWidget(online)
        top_layout.addSpacing(20)
        self.clock = QLabel()
        self.clock.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.clock.setStyleSheet("font-size:12px; font-weight:600; border:none; min-width:245px;")
        top_layout.addWidget(self.clock)
        right.addWidget(topbar)

        self.stack = QStackedWidget()
        self.dashboard = DashboardScreen()
        self.orbit = OrbitScreen()
        self.report = ReportScreen()
        self.satellite_data = SatelliteDataScreen()
        for key, page in (
            ("overview", self.dashboard),
            ("orbit", self.orbit),
            ("reports", self.report),
            ("data", self.satellite_data),
        ):
            self._pages[key] = page
            self.stack.addWidget(page)
        right.addWidget(self.stack, 1)
        outer.addLayout(right, 1)
        self.show_page("overview")

    def _connect_screens(self) -> None:
        self.dashboard.analysisReady.connect(self._analysis_ready)
        self.dashboard.openOrbit.connect(self.open_orbit)
        self.dashboard.openReport.connect(self.open_report)
        self.satellite_data.satelliteSelected.connect(self.dashboard.set_satellite)

    def _analysis_ready(self, result: dict) -> None:
        self.orbit.set_analysis(result)
        self.report.set_analysis(result)
        self.satellite_data.refresh()

    def _update_clock(self) -> None:
        self.clock.setText(QDateTime.currentDateTime().toString("ddd, MMM d yyyy   |   h:mm:ss AP"))

    def show_page(self, key: str) -> None:
        page = self._pages[key]
        self.stack.setCurrentWidget(page)
        for button_key, button in self._nav_buttons.items():
            active = button_key == key
            button.setChecked(active)
            button.setStyleSheet(
                "text-align:left; padding-left:14px; background:#0B4567; border:1px solid #00AEEF;"
                if active else
                "text-align:left; padding-left:14px; background:rgba(10,24,43,170); border:1px solid transparent;"
            )
        if key == "data":
            self.satellite_data.refresh()

    def _navigation_clicked(self, key: str, checked: bool) -> None:
        """Keep a selected navigation destination active when it is clicked twice."""
        if checked:
            self.show_page(key)
        else:
            self._nav_buttons[key].setChecked(True)

    def open_orbit(self, result: dict) -> None:
        if result:
            self.orbit.set_analysis(result)
        self.show_page("orbit")

    def open_report(self, result: dict) -> None:
        if result:
            self.report.set_analysis(result)
        self.show_page("reports")


class HyperMeshWindow(QMainWindow):
    """Own the windowed app, intro-to-workspace transition, and lock action."""

    def __init__(self, operator_name: str) -> None:
        super().__init__()
        self.setWindowTitle("HyperMesh AI | Orbital Intelligence")
        self.setMinimumSize(1000, 680)
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self.intro = IntroScreen()
        self.workspace = WorkspaceShell(operator_name)
        self._stack.addWidget(self.intro)
        self._stack.addWidget(self.workspace)
        self.intro.enterRequested.connect(lambda: self._stack.setCurrentWidget(self.workspace))
        self.workspace.lock_button.clicked.connect(self.lock_workspace)

    def lock_workspace(self) -> None:
        """Return to the credential gate without terminating the application."""
        self.hide()
        dialog = AuthDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_workspace = self.workspace
            self._stack.removeWidget(old_workspace)
            old_workspace.deleteLater()
            self.workspace = WorkspaceShell(dialog.username.text().strip())
            self._stack.insertWidget(1, self.workspace)
            self.workspace.lock_button.clicked.connect(self.lock_workspace)
            self._stack.setCurrentWidget(self.workspace)
            self.show()
        else:
            self.close()


def main() -> int:
    """Authenticate, apply the shared theme, and show a centered normal window."""
    app = QApplication(sys.argv)
    app.setApplicationName("HyperMesh AI")
    app.setOrganizationName("HyperMesh")
    apply_theme(app)

    try:
        auth = AuthDialog()
    except OSError as exc:
        QMessageBox.critical(None, "Local account unavailable", str(exc))
        return 1
    if auth.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = HyperMeshWindow(auth.username.text().strip())
    screen = app.primaryScreen()
    available = screen.availableGeometry() if screen else None
    width = min(1440, available.width() - 80) if available else 1440
    height = min(920, available.height() - 80) if available else 920
    window.resize(max(1000, width), max(680, height))
    if available:
        window.move(available.center() - window.rect().center())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
