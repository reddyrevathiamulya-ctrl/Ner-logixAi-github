"""
NER-LogixAI Risk Engine
Phase 5 foundation for NER-LogixAI.

Purpose:
- Analyze the 8 North-Eastern states of India.
- Consume the structure returned by data_loader.py without crashing
  when a source is empty/unavailable.
- Extract rainfall, flood and landslide evidence.
- Calculate transparent rule-based risk.
- Return stable JSON suitable for API, GIS, routes and frontend.
- Never invent a risk level when there is no usable evidence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services.data_loader import get_all_data_summary


# ============================================================
# NORTH-EASTERN STATES
# ============================================================

NORTH_EAST_STATES = [
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
]

STATE_ALIASES = {
    "arunachal": "Arunachal Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "sikkim": "Sikkim",
    "tripura": "Tripura",
}


# ============================================================
# RISK LEVELS
# ============================================================

RISK_LEVELS = {
    "UNKNOWN": 0,
    "LOW": 1,
    "MODERATE": 2,
    "HIGH": 3,
    "SEVERE": 4,
}


# ============================================================
# RAINFALL THRESHOLDS
# ============================================================

# Rainfall thresholds in mm/day.
# These are explicit and can be adjusted later if required.

RAINFALL_THRESHOLDS_MM = (
    (204.5, 4),
    (115.6, 4),
    (64.5, 3),
    (15.6, 2),
    (2.5, 1),
)


RAIN_KEYS = (
    "rainfall",
    "rain",
    "precipitation",
    "precip",
    "rain_mm",
    "rainfall_mm",
    "precipitation_mm",
    "daily_rainfall",
    "24h_rainfall",
)


FLOOD_KEYS = (
    "flood",
    "flood_risk",
    "flood_status",
    "flood_alert",
    "flood_severity",
    "water_level",
    "river_level",
    "flood_index",
)


LANDSLIDE_KEYS = (
    "landslide",
    "landslide_risk",
    "landslide_status",
    "landslide_alert",
    "landslide_severity",
    "landslide_index",
    "slope_risk",
)


STATUS_KEYS = (
    "risk",
    "status",
    "alert",
    "warning",
    "severity",
    "level",
    "condition",
)


# ============================================================
# SAFE HELPERS
# ============================================================

def _number(value: Any, default: float = 0.0) -> float:
    """Convert a value safely to float."""
    if value is None or isinstance(value, bool):
        return default

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
            return default

    return default


def _text(value: Any, default: str = "") -> str:
    """Convert any value safely to text."""
    if value is None:
        return default

    return str(value).strip()


def _key(value: Any) -> str:
    """Normalize dictionary keys."""
    return (
        _text(value)
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _canonical_state(value: Any) -> Optional[str]:
    """Return canonical North-East state name if recognized."""
    normalized = " ".join(
        _text(value)
        .lower()
        .replace("_", " ")
        .split()
    )

    return STATE_ALIASES.get(normalized)


def _risk_from_text(value: Any) -> int:
    """Convert textual risk/status information into 0-4."""
    text = _text(value).lower()

    if not text:
        return 0

    if any(
        word in text
        for word in (
            "extreme",
            "extremely high",
            "very high",
            "severe",
            "critical",
            "dangerous",
        )
    ):
        return 4

    if any(
        word in text
        for word in (
            "high",
            "danger",
            "warning",
            "red",
        )
    ):
        return 3

    if any(
        word in text
        for word in (
            "moderate",
            "medium",
            "alert",
            "yellow",
            "watch",
        )
    ):
        return 2

    if any(
        word in text
        for word in (
            "low",
            "normal",
            "safe",
            "green",
            "clear",
        )
    ):
        return 1

    return 0


def _is_number_like(value: Any) -> bool:
    """Check whether a value can safely be interpreted as a number."""
    if isinstance(value, bool):
        return False

    if isinstance(value, (int, float)):
        return True

    if isinstance(value, str):
        try:
            float(value.strip().replace(",", ""))
            return True
        except ValueError:
            return False

    return False


# ============================================================
# STATE DATA EXTRACTION
# ============================================================

def _find_state_data(
    data_summary: Any,
    state: str,
) -> Dict[str, Any]:
    """
    Find a state's data anywhere inside the loader output.

    Supports structures such as:

        {"Assam": {...}}

    and:

        {"states": [{"state": "Assam", ...}]}

    and nested dictionaries/lists.
    """

    if not isinstance(data_summary, (dict, list)):
        return {}

    wanted = _canonical_state(state) or state

    def search(value: Any) -> Dict[str, Any]:

        if isinstance(value, dict):

            # Direct state key.
            for key, item in value.items():

                if _canonical_state(key) == wanted:

                    if isinstance(item, dict):
                        return item

                    return {"value": item}

            # Record-style state fields.
            for field in (
                "state",
                "state_name",
                "stateName",
                "name",
            ):

                if field in value:

                    if _canonical_state(value[field]) == wanted:
                        return value

            # Recursive search.
            for item in value.values():

                found = search(item)

                if found:
                    return found

        elif isinstance(value, list):

            for item in value:

                found = search(item)

                if found:
                    return found

        return {}

    return search(data_summary)


# ============================================================
# CATEGORY DETECTION
# ============================================================

def _category_from_key(key: Any) -> Optional[str]:
    """Identify hazard category from a key."""

    normalized = _key(key)

    if any(
        token in normalized
        for token in (
            "rain",
            "precip",
            "weather",
        )
    ):
        return "rainfall"

    if (
        "flood" in normalized
        or "river_level" in normalized
    ):
        return "flood"

    if (
        "landslide" in normalized
        or "land_slide" in normalized
    ):
        return "landslide"

    return None


def _numeric_values(
    value: Any,
    results: Optional[List[float]] = None,
) -> List[float]:
    """Collect numeric values recursively."""

    if results is None:
        results = []

    if isinstance(value, dict):

        for item in value.values():
            _numeric_values(item, results)

    elif isinstance(value, list):

        for item in value:
            _numeric_values(item, results)

    elif _is_number_like(value):

        number = _number(value)

        if number >= 0:
            results.append(number)

    return results


def _find_category_values(
    value: Any,
    category: str,
) -> List[Tuple[str, Any]]:
    """
    Find values belonging to rainfall/flood/landslide categories.
    """

    found: List[Tuple[str, Any]] = []

    def walk(
        item: Any,
        parent_category: Optional[str] = None,
    ) -> None:

        if isinstance(item, dict):

            for key, child in item.items():

                child_category = (
                    _category_from_key(key)
                    or parent_category
                )

                if child_category == category:

                    found.append(
                        (
                            _text(key),
                            child,
                        )
                    )

                walk(
                    child,
                    child_category,
                )

        elif isinstance(item, list):

            for child in item:

                walk(
                    child,
                    parent_category,
                )

    walk(value)

    return found


# ============================================================
# NUMERIC SCORING
# ============================================================

def _rainfall_numeric_score(value: Any) -> int:
    """
    Score rainfall values when represented as mm/day.
    """

    if isinstance(value, dict):

        best = 0

        for key, child in value.items():

            # We recurse because rainfall data may be nested.
            child_score = _rainfall_numeric_score(child)

            best = max(
                best,
                child_score,
            )

        return best

    if isinstance(value, list):

        return max(
            (
                _rainfall_numeric_score(item)
                for item in value
            ),
            default=0,
        )

    if not _is_number_like(value):
        return 0

    mm = _number(value)

    for threshold, score in RAINFALL_THRESHOLDS_MM:

        if mm >= threshold:
            return score

    return 0


def _generic_numeric_score(value: Any) -> int:
    """
    Interpret existing flood/landslide score/index values
    when they are already on a 0-4 scale.
    """

    if isinstance(value, dict):

        best = 0

        for key, child in value.items():

            normalized = _key(key)

            if any(
                token in normalized
                for token in (
                    "score",
                    "index",
                    "risk",
                    "severity",
                    "level",
                )
            ):

                best = max(
                    best,
                    _generic_numeric_score(child),
                )

        return best

    if isinstance(value, list):

        return max(
            (
                _generic_numeric_score(item)
                for item in value
            ),
            default=0,
        )

    if not _is_number_like(value):
        return 0

    number = _number(value)

    if 0 <= number <= 4:
        return int(round(number))

    return 0


# ============================================================
# CATEGORY INSPECTION
# ============================================================

def _inspect_category(
    value: Any,
    category: str,
) -> Tuple[int, List[str]]:
    """Return score and evidence for one hazard category."""

    score = 0
    evidence: List[str] = []

    if isinstance(value, dict):

        for key, item in value.items():

            normalized = _key(key)

            # Textual status/risk fields.
            if any(
                normalized == field
                or normalized.endswith("_" + field)
                for field in STATUS_KEYS
            ):

                text_score = _risk_from_text(item)

                if text_score:

                    score = max(
                        score,
                        text_score,
                    )

                    evidence.append(
                        f"{_text(key)}="
                        f"{_text(item)}"
                        f" -> {text_score}/4"
                    )

            # Numeric rainfall.
            if category == "rainfall":

                numeric_score = _rainfall_numeric_score(item)

                if numeric_score:

                    score = max(
                        score,
                        numeric_score,
                    )

                    if _is_number_like(item):

                        evidence.append(
                            f"{_text(key)}="
                            f"{_number(item):g}"
                            f" -> {numeric_score}/4"
                        )

            # Numeric flood/landslide index.
            if category in (
                "flood",
                "landslide",
            ):

                numeric_score = _generic_numeric_score(item)

                if numeric_score:

                    score = max(
                        score,
                        numeric_score,
                    )

                    if _is_number_like(item):

                        evidence.append(
                            f"{_text(key)}="
                            f"{_number(item):g}"
                            f" -> {numeric_score}/4"
                        )

            child_score, child_evidence = (
                _inspect_category(
                    item,
                    category,
                )
            )

            score = max(
                score,
                child_score,
            )

            evidence.extend(
                child_evidence
            )

    elif isinstance(value, list):

        for item in value:

            child_score, child_evidence = (
                _inspect_category(
                    item,
                    category,
                )
            )

            score = max(
                score,
                child_score,
            )

            evidence.extend(
                child_evidence
            )

    elif isinstance(value, str):

        text_score = _risk_from_text(value)

        if text_score:

            score = max(
                score,
                text_score,
            )

            evidence.append(
                f"{value} -> {text_score}/4"
            )

    return score, evidence


# ============================================================
# CATEGORY CALCULATION
# ============================================================

def _calculate_category(
    state_data: Dict[str, Any],
    category: str,
) -> Tuple[int, List[str]]:
    """
    Calculate one hazard category.

    First searches explicit category sections.
    Then falls back to recursive inspection.
    """

    if not isinstance(state_data, dict):
        return 0, []

    score = 0
    evidence: List[str] = []

    category_values = _find_category_values(
        state_data,
        category,
    )

    for key, value in category_values:

        child_score, child_evidence = (
            _inspect_category(
                value,
                category,
            )
        )

        score = max(
            score,
            child_score,
        )

        if child_evidence:

            evidence.extend(
                f"{key}: {item}"
                for item in child_evidence
            )

    if not category_values:

        score, evidence = _inspect_category(
            state_data,
            category,
        )

    return score, evidence


# ============================================================
# RISK CALCULATION
# ============================================================

def calculate_risk(
    state_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate transparent rule-based risk for one state.

    No usable hazard evidence = UNKNOWN.

    The strongest available hazard indicator determines
    the current risk level.
    """

    if not isinstance(state_data, dict):
        state_data = {}

    rainfall_score, rainfall_evidence = (
        _calculate_category(
            state_data,
            "rainfall",
        )
    )

    flood_score, flood_evidence = (
        _calculate_category(
            state_data,
            "flood",
        )
    )

    landslide_score, landslide_evidence = (
        _calculate_category(
            state_data,
            "landslide",
        )
    )

    category_scores = {
        "rainfall": rainfall_score,
        "flood": flood_score,
        "landslide": landslide_score,
    }

    final_score = max(
        category_scores.values()
    )

    has_numeric_data = bool(
        _numeric_values(state_data)
    )

    if final_score >= 4:

        risk_level = "SEVERE"

    elif final_score == 3:

        risk_level = "HIGH"

    elif final_score == 2:

        risk_level = "MODERATE"

    elif final_score == 1:

        risk_level = "LOW"

    else:

        risk_level = "UNKNOWN"

    contributing_factors: List[str] = []

    if rainfall_score:

        contributing_factors.append(
            f"Rainfall/weather indicator: "
            f"{rainfall_score}/4"
        )

    if flood_score:

        contributing_factors.append(
            f"Flood indicator: "
            f"{flood_score}/4"
        )

    if landslide_score:

        contributing_factors.append(
            f"Landslide indicator: "
            f"{landslide_score}/4"
        )

    if not contributing_factors:

        contributing_factors.append(
            "No explicit usable hazard-risk "
            "indicator was available."
        )

    return {
        "risk_level": risk_level,
        "risk_score": final_score,
        "risk_scale": 4,

        "rainfall_score": rainfall_score,
        "flood_score": flood_score,
        "landslide_score": landslide_score,

        "has_numeric_data": has_numeric_data,

        "contributing_factors": (
            contributing_factors
        ),

        "evidence": {
            "rainfall": rainfall_evidence[:20],
            "flood": flood_evidence[:20],
            "landslide": landslide_evidence[:20],
        },
    }


# ============================================================
# NORTH-EAST ANALYSIS
# ============================================================

def analyze_north_east(
    data_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Analyze all 8 North-Eastern states."""

    results: List[Dict[str, Any]] = []

    for state in NORTH_EAST_STATES:

        state_data = _find_state_data(
            data_summary,
            state,
        )

        risk = calculate_risk(
            state_data
        )

        results.append(
            {
                "state": state,
                "risk": risk,
                "data_available": bool(
                    state_data
                ),
                "data": state_data,
            }
        )

    high_risk_states = [
        item["state"]
        for item in results
        if item["risk"]["risk_level"]
        in ("HIGH", "SEVERE")
    ]

    moderate_risk_states = [
        item["state"]
        for item in results
        if item["risk"]["risk_level"]
        == "MODERATE"
    ]

    data_available_states = [
        item["state"]
        for item in results
        if item["data_available"]
    ]

    return {
        "region": "North-Eastern India",

        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "states": results,

        "summary": {
            "total_states": len(
                NORTH_EAST_STATES
            ),

            "data_available_states": len(
                data_available_states
            ),

            "high_risk_states": (
                high_risk_states
            ),

            "moderate_risk_states": (
                moderate_risk_states
            ),

            "high_risk_count": len(
                high_risk_states
            ),

            "moderate_risk_count": len(
                moderate_risk_states
            ),
        },
    }


# ============================================================
# COMPATIBILITY ENTRY POINT
# ============================================================

def analyze_all_north_east(
    data_summary: Optional[Dict[str, Any]] = None,
    use_ollama: bool = False,
) -> Dict[str, Any]:
    """
    Main North-East analysis entry point.

    The use_ollama argument is retained for compatibility,
    but deterministic risk calculation does not require Ollama.
    """

    if data_summary is None:

        data_summary = (
            get_all_data_summary()
        )

    result = analyze_north_east(
        data_summary
    )

    result["analysis"] = {
        "method": (
            "transparent_rule_based"
        ),
        "ollama_used": False,
        "ollama_requested": bool(
            use_ollama
        ),
    }

    return result


# ============================================================
# CURRENT DATA ANALYSIS
# ============================================================

def analyze_current_data() -> Dict[str, Any]:
    """
    Load current data through data_loader.py
    and analyze all North-Eastern states.
    """

    data_summary = (
        get_all_data_summary()
    )

    return analyze_all_north_east(
        data_summary,
        use_ollama=False,
    )


# ============================================================
# GIS / ROUTE READY OUTPUT
# ============================================================

def get_state_risk_table(
    analysis: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Return compact state-level records suitable
    for GIS, maps, routes or frontend APIs.
    """

    if analysis is None:

        analysis = analyze_current_data()

    table: List[Dict[str, Any]] = []

    for item in analysis.get(
        "states",
        [],
    ):

        risk = item.get(
            "risk",
            {},
        )

        table.append(
            {
                "state": item.get(
                    "state"
                ),

                "risk_level": risk.get(
                    "risk_level",
                    "UNKNOWN",
                ),

                "risk_score": risk.get(
                    "risk_score",
                    0,
                ),

                "rainfall_score": risk.get(
                    "rainfall_score",
                    0,
                ),

                "flood_score": risk.get(
                    "flood_score",
                    0,
                ),

                "landslide_score": risk.get(
                    "landslide_score",
                    0,
                ),

                "data_available": bool(
                    item.get(
                        "data_available"
                    )
                ),
            }
        )

    return table


def get_high_risk_states(
    analysis: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Return states classified HIGH or SEVERE."""

    if analysis is None:

        analysis = (
            analyze_current_data()
        )

    return list(
        analysis.get(
            "summary",
            {},
        ).get(
            "high_risk_states",
            [],
        )
    )


# ============================================================
# JSON OUTPUT
# ============================================================

def print_analysis() -> None:
    """Print analysis as readable JSON."""

    try:

        result = (
            analyze_current_data()
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

    except Exception as exc:

        error = {
            "status": "error",
            "component": "risk_engine",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

        print(
            json.dumps(
                error,
                indent=2,
                ensure_ascii=False,
            )
        )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print_analysis()