from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

GIBS_TILE_TEMPLATE = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "{layer}/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
)
GIBS_CAPABILITIES_URL = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml"
)

# A tile inside the North Eastern Region used to verify a date actually
# serves tiles (capabilities can list dates that have no tiles yet).
_PROBE_TILE = {"z": 6, "y": 26, "x": 16}
_PROBE_MAX_ATTEMPTS = 6
_PROBE_TIMEOUT_SECONDS = 5

_CAPABILITIES_CACHE: dict[str, Any] = {"fetched_at": 0.0, "default_dates": {}, "range_dates": {}}
_CAPABILITIES_TTL_SECONDS = 6 * 3600

# Probing every layer serially makes the endpoint slow; keep a per-layer
# resolved date cache so probes happen at most once per day per layer.
_PROBE_CACHE: dict[str, str] = {}

_RANGE_PATTERN = re.compile(
    r"<Value>\s*(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})/(P\d+D)\s*</Value>"
)

SATELLITE_LAYERS: tuple[dict[str, Any], ...] = (
    {
        "id": "viirs_true_color",
        "name": "VIIRS true color",
        "provider": "NASA GIBS",
        "product": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
        "update_cadence": "daily or near-daily, cloud dependent",
        "best_for": "regional visual context",
    },
    {
        "id": "modis_true_color",
        "name": "MODIS true color",
        "provider": "NASA GIBS",
        "product": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "update_cadence": "daily, cloud dependent",
        "best_for": "regional visual context and change comparison",
    },
    {
        "id": "modis_flood",
        "name": "MODIS flood product",
        "provider": "NASA GIBS",
        "product": "MODIS_Combined_Flood_2-Day",
        "update_cadence": "acquisition dependent",
        "best_for": "broad flood screening, not road closure confirmation",
    },
)


def _parse_capabilities() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (default_date_by_layer, candidate_dates_by_layer).

    GIBS lists the Time dimension as a default date plus one or more
    ISO 8601 ranges (start/end/period). Real usable dates are within those
    ranges; the newest range end sometimes has no tiles yet, so candidates
    are probed before use.
    """
    now = time.time()
    cached = _CAPABILITIES_CACHE.get("default_dates")
    if cached is not None and now - _CAPABILITIES_CACHE["fetched_at"] < _CAPABILITIES_TTL_SECONDS:
        return _CAPABILITIES_CACHE["default_dates"], _CAPABILITIES_CACHE["range_dates"]

    default_dates: dict[str, str] = {}
    range_dates: dict[str, list[str]] = {}
    try:
        response = requests.get(
            GIBS_CAPABILITIES_URL,
            timeout=20,
            headers={"User-Agent": "NER-LogixAI/1.0"},
        )
        response.raise_for_status()
        content = response.text
    except requests.RequestException:
        return default_dates, range_dates

    for layer_match in re.finditer(r"<ows:Identifier>([^<]+)</ows:Identifier>", content):
        layer = layer_match.group(1)
        block = content[layer_match.end():layer_match.end() + 12000]

        default = re.search(r"<Default>(\d{4}-\d{2}-\d{2})</Default>", block)
        if default:
            default_dates[layer] = default.group(1)

        candidates: set[str] = set()
        for start, end, _period in _RANGE_PATTERN.findall(block):
            candidates.add(start)
            candidates.add(end)
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
                for offset in (1, 2, 3):
                    candidates.add((end_date - timedelta(days=offset)).isoformat())
            except ValueError:
                pass
        if default:
            candidates.add(default.group(1))
        if candidates:
            range_dates[layer] = sorted(candidates)

    _CAPABILITIES_CACHE["default_dates"] = default_dates
    _CAPABILITIES_CACHE["range_dates"] = range_dates
    _CAPABILITIES_CACHE["fetched_at"] = now
    return default_dates, range_dates


def _probe_date_serves_tiles(layer: str, date: str) -> bool:
    url = GIBS_TILE_TEMPLATE.format(
        layer=layer,
        date=date,
        z=_PROBE_TILE["z"],
        y=_PROBE_TILE["y"],
        x=_PROBE_TILE["x"],
    )
    try:
        response = requests.head(
            url,
            timeout=_PROBE_TIMEOUT_SECONDS,
            headers={"User-Agent": "NER-LogixAI/1.0"},
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def _resolve_date(layer: str) -> str:
    """Newest candidate date that actually serves tiles for the layer.

    Candidate dates come from the GIBS capabilities Time dimension (default
    date and recent range ends). We walk newest-to-oldest, bounded by
    _PROBE_MAX_ATTEMPTS, and return the first date whose tile serves.
    """
    default_dates, range_dates = _parse_capabilities()
    candidates = range_dates.get(layer) or []
    if not candidates:
        return datetime.now(timezone.utc).date().isoformat()

    ordered = sorted(set(candidates), reverse=True)[:_PROBE_MAX_ATTEMPTS]
    for date in ordered:
        if _probe_date_serves_tiles(layer, date):
            return date
    # Nothing served; prefer the capabilities default over "today".
    return default_dates.get(layer) or ordered[0]


def _latest_available_date(layer: str) -> str:
    """Newest date that serves tiles, with a per-layer probe cache."""
    cached = _PROBE_CACHE.get(layer)
    if cached is not None:
        return cached
    resolved = _resolve_date(layer)
    _PROBE_CACHE[layer] = resolved
    return resolved


def get_satellite_layers() -> dict[str, Any]:
    # Warm all layers in parallel so the first request is fast.
    products = [layer["product"] for layer in SATELLITE_LAYERS]
    with ThreadPoolExecutor(max_workers=len(products)) as executor:
        dates = dict(zip(products, executor.map(_latest_available_date, products)))

    layers = []
    for layer in SATELLITE_LAYERS:
        acquisition_date = dates[layer["product"]]
        item = dict(layer)
        item["tile_url_template"] = GIBS_TILE_TEMPLATE.format(
            layer=layer["product"],
            date=acquisition_date,
            z="{z}",
            y="{y}",
            x="{x}",
        )
        item["date"] = acquisition_date
        layers.append(item)

    return {
        "provider": "NASA Global Imagery Browse Services",
        "license_note": "Check NASA GIBS product terms before redistribution or caching.",
        "layers": layers,
        "refresh_policy": (
            "Capabilities are cached for 6 hours; advertised dates are "
            "validated against a real tile probe."
        ),
        "limitation": (
            "Optical imagery can be blocked by cloud cover and does not confirm "
            "a current road closure or newly falling landslide."
        ),
    }
