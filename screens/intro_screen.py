"""Purpose: branded introduction and entry point within the normal app window.

Inputs: local background/logo/audio assets from assets/.
Outputs: intro presentation and an enterRequested signal.
Connection: main.py listens for entry and switches to DashboardScreen.
"""

from pathlib import Path

from PySide6.QtCore import QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QPushButton, QVBoxLayout, QWidget

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


class IntroScreen(QWidget):
    """Animated opening screen; audio failure does not block the application."""

    enterRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("introScreen")
        self._background = QPixmap(str(ASSET_DIR / "background.png"))
        self._build_ui()
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self._fade = QPropertyAnimation(effect, b"opacity", self)
        self._fade.setDuration(1100)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 40, 24, 52)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QLabel()
        pixmap = QPixmap(str(ASSET_DIR / "logo2.png"))
        logo.setPixmap(
            pixmap.scaled(
                360, 360, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("AI-Powered Orbital Intelligence Platform")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 21px; color: #EAF7FF; letter-spacing: 1px;")
        enter = QPushButton("ENTER PLATFORM")
        enter.setFixedSize(250, 54)
        enter.setStyleSheet("font-size: 15px; letter-spacing: 2px;")
        enter.clicked.connect(self._enter_platform)
        layout.addStretch(1)
        layout.addWidget(logo)
        layout.addSpacing(8)
        layout.addWidget(subtitle)
        layout.addSpacing(26)
        layout.addWidget(enter, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

    def _enter_platform(self) -> None:
        """Switch from the introduction into the application workspace."""
        self.enterRequested.emit()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt event naming convention
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if not self._background.isNull():
            scaled = self._background.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.setOpacity(0.38)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
