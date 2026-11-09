"""Purpose: display the encounter's computed orbits and exact input-state telemetry.

Inputs: structured results from DashboardScreen and orbital calculations from
orbit_engine; the provided globe, background, and two HyperMesh logo assets.
Outputs: a static 3D orbit plot, satellite A/B markers, closest-approach marker,
and measurements tied to the submitted orbital records.
Connection: WorkspaceShell switches to this view and supplies each completed
encounter result. No animated or fabricated tracking stream is shown.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from engines.orbit_engine import EARTH_RADIUS_KM, satellite_state
from screens.space_widget import SpaceWidget
from screens.theme import CYAN, MUTED, make_panel

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


class OrbitCanvas(QWidget):
    """Draw two input-derived circular orbits around an Earth image."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(510)
        self.setStyleSheet("background:rgba(4,11,24,225); border:1px solid #173753; border-radius:16px;")
        self.analysis: dict = {}
        self.logo_a = QPixmap(str(ASSET_DIR / "logo.png"))
        self.logo_b = QPixmap(str(ASSET_DIR / "logo2.png"))
        self.earth_texture = self._load_earth_texture()

    @staticmethod
    def _load_earth_texture() -> QPixmap:
        """Use an Earth crop from the supplied background, or a drawn globe fallback."""
        background = QPixmap(str(ASSET_DIR / "background.png"))
        if background.isNull():
            return QPixmap()
        side = min(int(background.width() * 0.25), int(background.height() * 0.58))
        left = int(background.width() * 0.67)
        top = int(background.height() * 0.39)
        left = min(max(0, left), max(0, background.width() - side))
        top = min(max(0, top), max(0, background.height() - side))
        return background.copy(left, top, side, side)

    def set_analysis(self, analysis: dict) -> None:
        self.analysis = analysis
        self.update()

    @staticmethod
    def _camera(satellites: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Orient the view toward the objects so both markers are in front."""
        positions = [satellite_state(item)[0] for item in satellites]
        forward = np.sum([position / np.linalg.norm(position) for position in positions], axis=0)
        if np.linalg.norm(forward) < 1e-8:
            forward = positions[0]
        forward = forward / np.linalg.norm(forward)
        up_reference = np.array([0.0, 0.0, 1.0])
        right = np.cross(up_reference, forward)
        if np.linalg.norm(right) < 1e-8:
            right = np.array([1.0, 0.0, 0.0])
        else:
            right /= np.linalg.norm(right)
        up = np.cross(forward, right)
        up /= np.linalg.norm(up)
        return forward, right, up

    def _project(self, position: np.ndarray, right: np.ndarray, up: np.ndarray,
                 center: QPointF, radius: float) -> QPointF:
        return QPointF(
            center.x() + float(np.dot(position, right)) / EARTH_RADIUS_KM * radius,
            center.y() - float(np.dot(position, up)) / EARTH_RADIUS_KM * radius,
        )

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt event naming convention
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#040B18"))
        center = QPointF(self.width() * 0.48, self.height() * 0.53)
        earth_radius = min(self.height() * 0.31, self.width() * 0.27)

        front_paths = []
        back_paths = []
        orbit_specs = []
        if self.analysis:
            satellites = [
                self.analysis["satellites"]["a"],
                self.analysis["satellites"]["b"],
            ]
            forward, right, up = self._camera(satellites)
            orbit_colors = (QColor("#00AEEF"), QColor("#00FFFF"))
            for satellite, color, logo in zip(
                satellites, orbit_colors, (self.logo_a, self.logo_b)
            ):
                start_position, _ = satellite_state(satellite)
                period_seconds = (
                    2.0 * math.pi * float(np.linalg.norm(start_position))
                    / float(satellite["velocity"])
                )
                front_path = QPainterPath()
                back_path = QPainterPath()
                previous_front: bool | None = None
                point_count = 180
                for index in range(point_count + 1):
                    position, _ = satellite_state(
                        satellite, period_seconds * index / point_count
                    )
                    point = self._project(position, right, up, center, earth_radius)
                    is_front = float(np.dot(position, forward)) >= 0
                    path = front_path if is_front else back_path
                    if previous_front is None or is_front != previous_front:
                        path.moveTo(point)
                    else:
                        path.lineTo(point)
                    previous_front = is_front
                front_paths.append((color, front_path))
                back_paths.append((color, back_path))
                orbit_specs.append((satellite, color, logo, start_position))

            for color, path in back_paths:
                dim_color = QColor(color)
                dim_color.setAlpha(75)
                painter.setPen(QPen(dim_color, 2, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#17618A"))
        painter.drawEllipse(center, earth_radius, earth_radius)
        if not self.earth_texture.isNull():
            texture = self.earth_texture.scaled(
                int(earth_radius * 2), int(earth_radius * 2),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            clip = QPainterPath()
            clip.addEllipse(center, earth_radius, earth_radius)
            painter.save()
            painter.setClipPath(clip)
            painter.drawPixmap(
                int(center.x() - texture.width() / 2),
                int(center.y() - texture.height() / 2),
                texture,
            )
            painter.restore()
        painter.setPen(QPen(QColor(39, 193, 231, 150), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, earth_radius + 7, earth_radius + 7)

        if not self.analysis:
            painter.setPen(QColor("#D7E9F7"))
            painter.drawText(QPointF(26, 34), "Run an encounter analysis to plot satellite A and B.")
            return

        for color, path in front_paths:
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        icon_size = max(34, min(54, int(earth_radius * 0.36)))
        satellite_points = [
            self._project(position, right, up, center, earth_radius)
            for _, _, _, position in orbit_specs
        ]
        markers_overlap = (
            len(satellite_points) > 1
            and math.hypot(
                satellite_points[0].x() - satellite_points[1].x(),
                satellite_points[0].y() - satellite_points[1].y(),
            ) < icon_size * 1.3
        )
        for index, (satellite, color, logo, _) in enumerate(orbit_specs):
            point = satellite_points[index]
            marker_point = point
            if markers_overlap:
                marker_point = point + QPointF(
                    (2 * index - 1) * icon_size * 0.65,
                    -icon_size * 0.55,
                )
                painter.setPen(QPen(color, 1))
                painter.drawLine(point, marker_point)
                painter.setBrush(color)
                painter.drawEllipse(point, 3, 3)
            point = marker_point
            painter.setPen(QPen(color, 2))
            painter.setBrush(QColor("#071426"))
            painter.drawEllipse(point, icon_size * 0.60, icon_size * 0.60)
            if not logo.isNull():
                icon = logo.scaled(
                    icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(
                    int(point.x() - icon.width() / 2),
                    int(point.y() - icon.height() / 2),
                    icon,
                )
            painter.setPen(QColor("#F4F8FF"))
            label = "SATELLITE A" if satellite is satellites[0] else "SATELLITE B"
            painter.drawText(QPointF(point.x() + icon_size * 0.60, point.y() + 4), label)

        close = self.analysis.get("collision_point")
        if close:
            latitude = math.radians(float(close["latitude"]))
            longitude = math.radians(float(close["longitude"]))
            point_vector = (EARTH_RADIUS_KM + float(close["altitude"])) * np.array(
                [
                    math.cos(latitude) * math.cos(longitude),
                    math.cos(latitude) * math.sin(longitude),
                    math.sin(latitude),
                ]
            )
            marker = self._project(point_vector, right, up, center, earth_radius)
            painter.setPen(QPen(QColor("#FF4D6D"), 3))
            painter.drawLine(QPointF(marker.x() - 10, marker.y()), QPointF(marker.x() + 10, marker.y()))
            painter.drawLine(QPointF(marker.x(), marker.y() - 10), QPointF(marker.x(), marker.y() + 10))
            painter.setPen(QColor("#FF8A9D"))
            painter.drawText(QPointF(marker.x() + 14, marker.y() - 8), "CLOSEST APPROACH")

        painter.setPen(QColor("#B4C7D9"))
        painter.drawText(QPointF(22, 30), "ORBIT PATHS FROM PROVIDED POSITION, ALTITUDE & INCLINATION")


class OrbitScreen(SpaceWidget):
    """Present exact encounter measurements and an input-derived orbit plot."""

    def __init__(self) -> None:
        super().__init__()
        self.analysis: dict = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(38, 30, 38, 32)
        heading = QLabel("ORBITAL TRACKING")
        heading.setStyleSheet("font-size:26px; font-weight:800; letter-spacing:1px;")
        subheading = QLabel("Satellite positions and orbit paths calculated from the selected orbital records.")
        subheading.setStyleSheet(f"font-size:14px; color:{MUTED};")
        root.addWidget(heading)
        root.addWidget(subheading)

        content = QHBoxLayout()
        content.setSpacing(18)
        self.canvas = OrbitCanvas()
        content.addWidget(self.canvas, 7)
        panel, layout = make_panel("TRACKING DATA")
        self.satellite_cards: dict[str, QLabel] = {}
        for slot, logo, accent in (
            ("a", self.canvas.logo_a, CYAN),
            ("b", self.canvas.logo_b, "#00AEEF"),
        ):
            card = QWidget()
            row = QHBoxLayout(card)
            row.setContentsMargins(2, 4, 2, 4)
            icon = QLabel()
            if not logo.isNull():
                icon.setPixmap(logo.scaled(
                    58, 58, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            row.addWidget(icon)
            text = QVBoxLayout()
            name = QLabel(f"SATELLITE {slot.upper()}")
            name.setStyleSheet(f"font-size:12px; color:{accent}; font-weight:800;")
            value = QLabel("No analyzed record")
            value.setWordWrap(True)
            value.setStyleSheet("font-size:13px; color:#E4EDF7;")
            self.satellite_cards[slot] = value
            text.addWidget(name)
            text.addWidget(value)
            row.addLayout(text, 1)
            layout.addWidget(card)

        for key, title in (
            ("approach", "CLOSEST APPROACH"),
            ("velocity", "RELATIVE VELOCITY"),
            ("time", "TIME TO CLOSEST APPROACH"),
            ("point", "PREDICTED CLOSE POINT"),
        ):
            label = QLabel(title)
            label.setStyleSheet(f"font-size:10px; color:{CYAN}; font-weight:800; letter-spacing:1px;")
            value = QLabel("Awaiting analysis")
            value.setWordWrap(True)
            value.setStyleSheet("font-size:14px; color:#D9E7F5;")
            self.satellite_cards[key] = value
            layout.addWidget(label)
            layout.addWidget(value)
        layout.addStretch()
        note = QLabel("A plotted estimate, not a live tracking feed.")
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size:10px; color:{MUTED};")
        layout.addWidget(note)
        content.addWidget(panel, 3)
        root.addLayout(content, 1)

    def set_analysis(self, analysis: dict) -> None:
        """Update the view exclusively from the current analysis result."""
        self.analysis = analysis
        self.canvas.set_analysis(analysis)
        satellites = analysis["satellites"]
        for slot in ("a", "b"):
            item = satellites[slot]
            self.satellite_cards[slot].setText(
                f"{item['name']}\n"
                f"{float(item['latitude']):.3f}°, {float(item['longitude']):.3f}°\n"
                f"{float(item['altitude']):.1f} km  ·  {float(item['velocity']):.2f} km/s"
            )
        self.satellite_cards["approach"].setText(
            f"{analysis['closest_approach_km']:.2f} km"
        )
        self.satellite_cards["velocity"].setText(
            f"{analysis['relative_velocity_kms']:.2f} km/s"
        )
        self.satellite_cards["time"].setText(
            f"{analysis['time_to_closest_hours']:.2f} hours"
        )
        point = analysis["collision_point"]
        self.satellite_cards["point"].setText(
            f"{point['latitude']:.2f}°, {point['longitude']:.2f}°\n"
            f"Altitude {point['altitude']:.1f} km"
        )
