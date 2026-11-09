"""Purpose: reusable screen base that paints the provided space background.

Inputs: the shared assets/background.png image and QWidget resize events.
Outputs: a darkened, legible space-themed canvas behind screen content.
Connection: dashboard, orbital tracking, report, and satellite data screens inherit
this widget so the supplied background is used consistently across the app.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


class SpaceWidget(QWidget):
    """Draw the shared background while leaving child widgets responsible for UI."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._background = QPixmap(str(ASSET_DIR / "background.png"))
        self.setStyleSheet("background: transparent;")
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt event naming convention
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#050816"))
        if not self._background.isNull():
            scaled = self._background.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(
                (self.width() - scaled.width()) // 2,
                (self.height() - scaled.height()) // 2,
                scaled,
            )
            painter.fillRect(self.rect(), QColor(5, 8, 22, 185))
