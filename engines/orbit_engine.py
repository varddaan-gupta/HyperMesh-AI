"""Purpose: lightweight Earth-centered orbital geometry and propagation helpers.

Inputs: satellite records containing latitude, longitude, altitude, velocity,
and inclination, plus an optional propagation interval in seconds.
Outputs: Cartesian position/velocity estimates and geodetic display values.
Connection: prediction_engine uses these estimates for closest-approach math;
orbit_screen uses them to plot the inferred orbital paths.
"""

from __future__ import annotations

import math

import numpy as np

EARTH_RADIUS_KM = 6371.0
EARTH_MU_KM3_S2 = 398600.4418


def satellite_state(satellite: dict, seconds: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Return an inferred circular-orbit ECEF position (km) and velocity (km/s)."""
    latitude = math.radians(float(satellite["latitude"]))
    longitude = math.radians(float(satellite["longitude"]))
    altitude = float(satellite["altitude"])
    speed = float(satellite["velocity"])
    inclination = math.radians(float(satellite["inclination"]))
    radius = EARTH_RADIUS_KM + altitude

    radial = np.array(
        [math.cos(latitude) * math.cos(longitude),
         math.cos(latitude) * math.sin(longitude),
         math.sin(latitude)],
        dtype=float,
    )
    east = np.array([-math.sin(longitude), math.cos(longitude), 0.0], dtype=float)
    north = np.array(
        [-math.sin(latitude) * math.cos(longitude),
         -math.sin(latitude) * math.sin(longitude),
         math.cos(latitude)],
        dtype=float,
    )
    cos_latitude = math.cos(latitude)
    if cos_latitude < 1e-12:
        normal_north = 0.0
    else:
        normal_north = math.cos(inclination) / cos_latitude
    normal_north = max(-1.0, min(1.0, normal_north))
    normal_east = -math.sqrt(max(0.0, 1.0 - normal_north**2))
    orbit_normal = normal_east * east + normal_north * north
    direction = np.cross(orbit_normal, radial)
    direction /= np.linalg.norm(direction)
    phase = speed * float(seconds) / radius
    position = radius * (radial * math.cos(phase) + direction * math.sin(phase))
    velocity = speed * (-radial * math.sin(phase) + direction * math.cos(phase))
    return position, velocity


def geodetic_position(position: np.ndarray) -> dict[str, float]:
    """Convert a Cartesian position estimate into latitude, longitude, altitude."""
    x, y, z = (float(value) for value in position)
    radius = float(np.linalg.norm(position))
    return {
        "latitude": math.degrees(math.asin(max(-1.0, min(1.0, z / radius)))),
        "longitude": math.degrees(math.atan2(y, x)),
        "altitude": radius - EARTH_RADIUS_KM,
    }


def orbital_speed(altitude_km: float) -> float:
    """Return the circular-orbit speed estimate for a given altitude."""
    return math.sqrt(EARTH_MU_KM3_S2 / (EARTH_RADIUS_KM + float(altitude_km)))
