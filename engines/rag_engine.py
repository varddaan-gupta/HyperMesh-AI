"""Purpose: lightweight local retrieval and structured encounter explanations.

Inputs: prediction results, satellite records, and data/knowledge.json.
Outputs: similar historical cases and a deterministic plain-language explanation.
Connection: called after prediction, then its result is shown in the mission
report and saved back into knowledge.json for future local retrieval.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_PATH = ROOT / "data" / "knowledge.json"
TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")


def _load_knowledge() -> dict:
    """Read the local knowledge base and fail clearly if it is malformed."""
    if not KNOWLEDGE_PATH.exists():
        return {"cases": [], "generated_reports": []}
    with KNOWLEDGE_PATH.open("r", encoding="utf-8") as file:
        contents = json.load(file)
    if not isinstance(contents, dict) or not isinstance(contents.get("cases"), list):
        raise ValueError(f"{KNOWLEDGE_PATH} must contain a 'cases' list.")
    contents.setdefault("generated_reports", [])
    return contents


def _case_text(case: dict) -> str:
    return " ".join(
        str(case.get(key, ""))
        for key in ("risk_level", "summary", "features", "altitude_band", "outcome")
    )


def _tfidf_similarity(documents: list[str], query_index: int) -> list[float]:
    """Compute cosine similarity with smoothed TF-IDF using the standard library."""
    tokenized = [
        Counter(token.lower() for token in TOKEN_PATTERN.findall(document))
        for document in documents
    ]
    document_frequency: Counter[str] = Counter()
    for frequencies in tokenized:
        document_frequency.update(frequencies.keys())

    document_count = len(tokenized)
    inverse_frequency = {
        term: math.log((1 + document_count) / (1 + frequency)) + 1.0
        for term, frequency in document_frequency.items()
    }

    def vector(frequencies: Counter[str]) -> dict[str, float]:
        weights = {
            term: count * inverse_frequency[term]
            for term, count in frequencies.items()
            if term in inverse_frequency
        }
        magnitude = math.sqrt(sum(weight * weight for weight in weights.values()))
        if magnitude:
            return {term: weight / magnitude for term, weight in weights.items()}
        return {}

    vectors = [vector(frequencies) for frequencies in tokenized]
    query = vectors[query_index]
    return [
        sum(weight * vectors[index].get(term, 0.0) for term, weight in query.items())
        for index in range(len(documents))
        if index != query_index
    ]


def retrieve_similar_cases(result: dict, limit: int = 3) -> list[dict]:
    """Rank local cases by TF-IDF similarity to the current encounter."""
    cases = _load_knowledge()["cases"]
    if not cases:
        return []
    current = {
        "risk_level": result["risk_level"],
        "summary": (
            f"{result['altitude_difference_km']:.1f} km altitude difference; "
            f"{result['relative_velocity_kms']:.2f} km/s relative velocity; "
            f"{result['closest_approach_km']:.1f} km closest approach"
        ),
        "features": f"{result['risk_level']} orbital encounter",
    }
    documents = [_case_text(case) for case in cases] + [_case_text(current)]
    scores = _tfidf_similarity(documents, len(documents) - 1)
    ranked_indices = sorted(range(len(cases)), key=lambda index: scores[index], reverse=True)
    matches = []
    for index in ranked_indices[: max(0, limit)]:
        case = dict(cases[index])
        case["similarity"] = scores[index]
        matches.append(case)
    return matches


def explain_encounter(result: dict, similar_cases: list[dict]) -> str:
    """Build a transparent, template-based explanation without an LLM."""
    count = len(similar_cases)
    risk = result["risk_level"].lower()
    altitude_gap = result["altitude_difference_km"]
    relative_speed = result["relative_velocity_kms"]
    if count:
        similar_risk_count = sum(
            case.get("risk_level", "").upper() == result["risk_level"] for case in similar_cases
        )
        comparison = (
            f"The current scenario resembles {count} local historical "
            f"{'case' if count == 1 else 'cases'}; {similar_risk_count} share the "
            f"{result['risk_level']} risk category."
        )
    else:
        comparison = "No historical cases are stored yet; this assessment uses orbital geometry only."
    drivers = []
    drivers.append("the altitude separation is small" if altitude_gap < 25 else "the altitude separation is moderate")
    drivers.append("relative velocity is high" if relative_speed >= 5 else "relative velocity is comparatively low")
    return (
        f"This is a {risk}-risk screening result with a modeled collision probability of "
        f"{result['collision_probability']:.1%}. The closest-approach estimate is "
        f"{result['closest_approach_km']:.1f} km in approximately "
        f"{result['time_to_closest_hours']:.2f} hours. The main indicators are that "
        f"{drivers[0]} and {drivers[1]} ({relative_speed:.2f} km/s). {comparison} "
        "This hackathon prototype uses simplified circular-orbit propagation and is not an "
        "operational conjunction assessment."
    )


def record_encounter(result: dict, explanation: str, similar_cases: list[dict]) -> None:
    """Persist an analyzed encounter for future local retrieval."""
    knowledge = _load_knowledge()
    satellites = result["satellites"]
    knowledge["cases"].append(
        {
            "id": f"HM-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "risk_level": result["risk_level"],
            "summary": explanation,
            "features": (
                f"altitude difference {result['altitude_difference_km']:.1f} km "
                f"relative velocity {result['relative_velocity_kms']:.2f} km/s"
            ),
            "similar_case_ids": [case.get("id", "") for case in similar_cases],
            "altitude_band": f"{int(min(float(satellites['a']['altitude']), float(satellites['b']['altitude'])) // 100) * 100} km band",
            "outcome": "screening estimate; no confirmed collision outcome",
        }
    )
    knowledge["cases"] = knowledge["cases"][-200:]
    with KNOWLEDGE_PATH.open("w", encoding="utf-8") as file:
        json.dump(knowledge, file, indent=2)


def record_report(result: dict, report_text: str) -> None:
    """Save generated mission report text in the local knowledge base."""
    knowledge = _load_knowledge()
    knowledge["generated_reports"].append(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "risk_level": result["risk_level"],
            "satellites": [
                result["satellites"]["a"]["name"],
                result["satellites"]["b"]["name"],
            ],
            "report": report_text,
        }
    )
    knowledge["generated_reports"] = knowledge["generated_reports"][-100:]
    with KNOWLEDGE_PATH.open("w", encoding="utf-8") as file:
        json.dump(knowledge, file, indent=2)
