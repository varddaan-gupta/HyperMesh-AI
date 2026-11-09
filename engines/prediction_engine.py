"""Purpose: deterministic, local-only satellite encounter risk estimation.

Inputs: two satellite dictionaries with name, latitude/longitude (degrees),
altitude (km), velocity (km/s), and inclination (degrees).
Outputs: closest-approach geometry, probability, risk category, confidence,
and future-position estimates. No network or language model is used.
Connection: dashboard runs predict_encounter; orbital tracking and report
screens render its structured result.
"""

from __future__ import annotations

import math

import numpy as np

from engines.orbit_engine import geodetic_position, satellite_state

RISK_THRESHOLDS = ((0.75, "CRITICAL"), (0.35, "HIGH"), (0.10, "MEDIUM"))


def validate_satellite(record: dict) -> None:
    """Validate all required orbital fields and physical input ranges."""
    required = ("name", "latitude", "longitude", "altitude", "velocity", "inclination")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"Satellite record is missing: {', '.join(missing)}")
    for field in required[1:]:
        value = float(record[field])
        if not math.isfinite(value):
            raise ValueError(f"{field.title()} must be a finite number.")
    if not -90 <= float(record["latitude"]) <= 90:
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not -180 <= float(record["longitude"]) <= 180:
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if float(record["altitude"]) < 0:
        raise ValueError("Altitude cannot be negative.")
    if float(record["velocity"]) <= 0:
        raise ValueError("Velocity must be greater than zero.")
    if not 0 <= float(record["inclination"]) <= 180:
        raise ValueError("Inclination must be between 0 and 180 degrees.")
    latitude = math.radians(float(record["latitude"]))
    inclination = math.radians(float(record["inclination"]))
    if abs(math.sin(latitude)) > abs(math.sin(inclination)) + 1e-9:
        raise ValueError("Latitude is outside the ground track allowed by this inclination.")


def predict_encounter(satellite_a: dict, satellite_b: dict, horizon_hours: float = 24.0) -> dict:
    """Estimate the encounter using circular-orbit propagation and uncertainty."""
    validate_satellite(satellite_a)
    validate_satellite(satellite_b)
    if not math.isfinite(horizon_hours) or horizon_hours <= 0:
        raise ValueError("Prediction horizon must be a positive number of hours.")

    horizon_seconds = horizon_hours * 3600.0

    def separation_at(seconds: float) -> float:
        propagated_a, _ = satellite_state(satellite_a, seconds)
        propagated_b, _ = satellite_state(satellite_b, seconds)
        return float(np.linalg.norm(propagated_b - propagated_a))

    sample_count = max(2, int(math.ceil(horizon_seconds / 120.0)) + 1)
    sample_times = np.linspace(0.0, horizon_seconds, sample_count)
    sample_distances = np.array([separation_at(float(seconds)) for seconds in sample_times])
    closest_index = int(np.argmin(sample_distances))
    time_to_closest = float(sample_times[closest_index])
    if 0 < closest_index < len(sample_times) - 1:
        left = float(sample_times[closest_index - 1])
        right = float(sample_times[closest_index + 1])
        golden_ratio = (math.sqrt(5.0) - 1.0) / 2.0
        point_c = right - golden_ratio * (right - left)
        point_d = left + golden_ratio * (right - left)
        distance_c = separation_at(point_c)
        distance_d = separation_at(point_d)
        for _ in range(36):
            if distance_c <= distance_d:
                right, point_d, distance_d = point_d, point_c, distance_c
                point_c = right - golden_ratio * (right - left)
                distance_c = separation_at(point_c)
            else:
                left, point_c, distance_c = point_c, point_d, distance_d
                point_d = left + golden_ratio * (right - left)
                distance_d = separation_at(point_d)
        time_to_closest = (left + right) / 2.0

    closest_a, velocity_a = satellite_state(satellite_a, time_to_closest)
    closest_b, velocity_b = satellite_state(satellite_b, time_to_closest)
    speed = float(np.linalg.norm(velocity_b - velocity_a))
    miss_distance = float(np.linalg.norm(closest_b - closest_a))
    altitude_gap = abs(float(satellite_a["altitude"]) - float(satellite_b["altitude"]))
    # A conservative encounter envelope makes this prototype useful for screening;
    # it is not a substitute for covariance-based operational conjunction analysis.
    combined_uncertainty_km = 2.0 + min(18.0, altitude_gap * 0.04)
    normalized_miss = miss_distance / combined_uncertainty_km
    probability = float(1.0 / (1.0 + math.exp(min(60.0, max(-60.0, 4.0 * (normalized_miss - 1.0))))))
    velocity_factor = min(1.0, speed / 15.0)
    probability = min(1.0, probability * (0.75 + velocity_factor * 0.25))
    if miss_distance > 250.0:
        probability *= math.exp(-(miss_distance - 250.0) / 100.0)
    probability = float(np.clip(probability, 0.0, 1.0))

    risk_level = next((name for threshold, name in RISK_THRESHOLDS if probability >= threshold), "LOW")
    data_completeness = 1.0 if all(
        field in satellite_a and field in satellite_b
        for field in ("latitude", "longitude", "altitude", "velocity", "inclination")
    ) else 0.7
    confidence = float(np.clip(0.55 + 0.25 * data_completeness + 0.15 * min(speed / 10.0, 1.0), 0, 0.98))

    future_seconds = min(horizon_seconds, max(0.0, time_to_closest))
    predicted_a, _ = satellite_state(satellite_a, future_seconds)
    predicted_b, _ = satellite_state(satellite_b, future_seconds)
    midpoint = (closest_a + closest_b) / 2.0
    trajectory_samples = [
        {
            "object": satellite_a["name"],
            "x_km": float(closest_a[0]),
            "y_km": float(closest_a[1]),
            "z_km": float(closest_a[2]),
        },
        {
            "object": satellite_b["name"],
            "x_km": float(closest_b[0]),
            "y_km": float(closest_b[1]),
            "z_km": float(closest_b[2]),
        },
    ]

    return {
        "satellites": {"a": dict(satellite_a), "b": dict(satellite_b)},
        "risk_level": risk_level,
        "collision_probability": probability,
        "confidence": confidence,
        "closest_approach_km": miss_distance,
        "relative_velocity_kms": speed,
        "time_to_closest_hours": time_to_closest / 3600.0,
        "altitude_difference_km": altitude_gap,
        "collision_point": geodetic_position(midpoint),
        "closest_positions": {
            "a": geodetic_position(closest_a),
            "b": geodetic_position(closest_b),
        },
        "future_positions": {
            "a": geodetic_position(predicted_a),
            "b": geodetic_position(predicted_b),
        },
        "trajectory_samples": trajectory_samples,
        "suggested_action": (
            "Initiate collision-avoidance planning and validate with authoritative tracking data."
            if risk_level in ("HIGH", "CRITICAL")
            else "Continue monitoring and refresh orbital state estimates."
            if risk_level == "MEDIUM"
            else "Maintain routine monitoring; no immediate maneuver is indicated."
        ),
    }
