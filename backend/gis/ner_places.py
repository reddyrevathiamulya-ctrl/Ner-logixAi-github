from __future__ import annotations

import json
from pathlib import Path

_PLACES_PATH = Path(__file__).resolve().parent / "ner_places.json"

_PLACES: dict | None = None


def _load_places() -> dict:
    global _PLACES
    if _PLACES is None:
        try:
            _PLACES = json.loads(_PLACES_PATH.read_text(encoding="utf-8"))["places"]
        except (OSError, ValueError, KeyError):
            _PLACES = {}
    return _PLACES


def normalize(text: str) -> str:
    return " ".join(text.lower().replace(",", " ").split())


def _state_mentioned(query: str, state_key: str) -> bool:
    """True when the query text names this state (e.g. 'tripura' in 'udaipur, tripura')."""
    state_word = state_key.split()[0]
    return state_word in normalize(query)


def lookup_place(query: str) -> dict | None:
    """Return a curated NER place record for a matching district or HQ town.

    Match priority:
      1. District name match (e.g. "Anjaw", "North Tripura").
      2. HQ town match when the state is named in the query (e.g. "Udaipur, Tripura")
         or the town is unambiguous within NER.
    """
    if not query:
        return None
    normalized = normalize(query)

    district_matches = []
    town_matches = []
    for state_key, state_places in _load_places().items():
        for district_key, record in state_places.items():
            district_words = normalize(district_key)
            town_words = normalize(record.get("town", ""))
            name_words = normalize(record.get("name", ""))
            if district_words in normalized:
                district_matches.append((state_key, district_key, record))
            elif town_words in normalized or name_words in normalized:
                town_matches.append((state_key, district_key, record))

    candidates = district_matches or town_matches
    if not candidates:
        return None

    def _result(state_key: str, district_key: str, record: dict) -> dict:
        return {
            "name": record["name"],
            "lat": record["lat"],
            "lon": record["lon"],
            "source": record.get("source", "curated NER reference table"),
            "district": record.get("district", district_key),
        }

    # Prefer the candidate whose state is named in the query.
    for state_key, district_key, record in candidates:
        if _state_mentioned(normalized, state_key):
            return _result(state_key, district_key, record)

    # Otherwise prefer district-name matches over town matches, then the
    # first remaining candidate.
    if district_matches:
        state_key, district_key, record = district_matches[0]
    else:
        state_key, district_key, record = candidates[0]
    return _result(state_key, district_key, record)


def list_places() -> list[dict]:
    records = []
    for state_places in _load_places().values():
        for key, record in state_places.items():
            records.append(
                {
                    "key": key,
                    "name": record.get("name", key),
                    "town": record.get("town", key),
                    "district": record.get("district", key),
                    "lat": record["lat"],
                    "lon": record["lon"],
                }
            )
    return records