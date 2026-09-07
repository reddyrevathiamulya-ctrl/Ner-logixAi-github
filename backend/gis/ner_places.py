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
      2. HQ town / village match when the state is named in the query
         (e.g. "Udaipur, Tripura") or the town is unambiguous within NER.
      3. Alias match: entries may carry an "aliases" list (e.g. common
         alternate spellings such as "Tiangnuam" for Tlangnuam) so demo
         lookups do not fail on a spelling variant.
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
            elif any(
                normalize(alias) in normalized
                for alias in record.get("aliases", [])
                if isinstance(alias, str) and alias.strip()
            ):
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


_STATE_TITLES = {
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "sikkim": "Sikkim",
    "tripura": "Tripura",
}


def _state_title(state_key: str) -> str:
    return _STATE_TITLES.get(state_key, state_key.replace("_", " ").title())


def search_places(query: str, limit: int = 10) -> list[dict]:
    """Autocomplete over curated NER places (district HQs + demo places).

    A record matches when every query token appears in at least one of its
    fields (town, display name, aliases, district, state, or slug). Results
    are ranked by how close the match is to the place's own name, so typing
    a town prefix ("sohr") or a demo alias ("cherrapunji") surfaces the
    right pin before broader district or state matches.
    """
    normalized = normalize(query)
    if not normalized:
        return []
    tokens = normalized.split()
    ranked: list[tuple[float, dict]] = []

    for state_key, state_places in _load_places().items():
        state_text = normalize(state_key)
        for key, record in state_places.items():
            town = normalize(record.get("town", ""))
            name = normalize(record.get("name", ""))
            aliases = " ".join(
                normalize(alias)
                for alias in record.get("aliases", [])
                if isinstance(alias, str) and alias.strip()
            )
            district = normalize(record.get("district", ""))
            slug = normalize(key)

            fields = (town, name, aliases, district, state_text, slug)
            if not any(
                all(token in field for token in tokens)
                for field in fields
                if field
            ):
                continue

            # Weight by which field matched and how much of the query is a
            # prefix of it (prefix beats a mere substring hit).
            score = 0.0
            for weight, field in (
                (10.0, town),
                (9.0, name),
                (9.0, aliases),
                (6.0, district),
                (4.0, slug),
                (2.0, state_text),
            ):
                if not field or not all(token in field for token in tokens):
                    continue
                if field.startswith(normalized):
                    score = max(score, weight + 3.0)
                elif any(
                    word.startswith(token)
                    for word in field.split()
                    for token in tokens
                ):
                    score = max(score, weight + 1.5)
                else:
                    score = max(score, weight)

            display = record.get("name", record.get("town") or key)
            base = display.split(" (", 1)[0].strip()
            ranked.append(
                (
                    score,
                    {
                        "key": key,
                        "name": display,
                        "town": record.get("town", base),
                        # Geocodable fill text: never includes the district
                        # name, because lookup_place prefers a district-key
                        # match and would otherwise pin the HQ town.
                        "label": base,
                        "district": record.get("district", key),
                        "state": _state_title(state_key),
                        "kind": "demo" if "demo" in record.get("source", "") else "district_hq",
                        "lat": record["lat"],
                        "lon": record["lon"],
                    },
                )
            )

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[: max(1, min(int(limit), 50))]]