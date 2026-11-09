"""Purpose: shared dark-space visual language and reusable widget helpers.

Inputs: QApplication or screen widgets.
Outputs: consistent palette, typography, and glass-style panel styling.
Connection: called by main.py and imported by all application screens.
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout

BACKGROUND = "#050816"
PRIMARY = "#00AEEF"
CYAN = "#00FFFF"
TEXT = "#F4F8FF"
MUTED = "#91A3BB"

APP_STYLESHEET = """
QWidget { color: #F4F8FF; background: #050816; font-family: "Segoe UI"; font-size: 14px; }
QLabel { background: transparent; }
QLineEdit, QComboBox, QSpinBox {
  color: #F4F8FF; background: rgba(11, 25, 47, 220); border: 1px solid #24415F;
  border-radius: 9px; padding: 10px 12px; selection-background-color: #00AEEF;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #00FFFF; }
QPushButton {
  color: #F4F8FF; background: #087FB5; border: 1px solid #00AEEF;
  border-radius: 10px; padding: 11px 18px; font-weight: 700;
}
QPushButton:hover { background: #099CCC; }
QPushButton:pressed { background: #05658F; }
QPushButton:disabled { color: #72839A; background: #172436; border-color: #26364A; }
QTextBrowser { background: rgba(7, 17, 34, 235); border: 1px solid #203957; border-radius: 12px; padding: 14px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 9px; background: #081225; }
QScrollBar::handle:vertical { background: #1A5275; border-radius: 4px; min-height: 28px; }
"""


def apply_theme(app: QApplication) -> None:
    """Install the global palette, stylesheet, and default font."""
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLESHEET)


def make_panel(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    """Create a reusable translucent panel and its content layout."""
    panel = QFrame()
    panel.setObjectName("glassPanel")
    panel.setStyleSheet(
        "#glassPanel { background: rgba(10, 23, 43, 220); border: 1px solid #1A3958; border-radius: 16px; }"
    )
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 18, 20, 20)
    layout.setSpacing(12)
    if title:
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 17px; font-weight: 700; color: #F4F8FF; border: none;")
        layout.addWidget(heading)
    return panel, layout
