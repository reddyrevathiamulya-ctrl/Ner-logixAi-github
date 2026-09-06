from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

GIBS_TILE_TEMPLATE = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "{layer}/default/{date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
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
        "product": "MODIS_Terra_Flood_2Day",
        "update_cadence": "product dependent",
        "best_for": "broad flood screening, not road closure confirmation",
    },
)


def get_satellite_layers() -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    layers = []
    for layer in SATELLITE_LAYERS:
        item = dict(layer)
        item["tile_url_template"] = GIBS_TILE_TEMPLATE.format(
            layer=layer["product"],
            date=today,
            z="{z}",
            y="{y}",
            x="{x}",
        )
        item["date"] = today
        layers.append(item)

    return {
        "provider": "NASA Global Imagery Browse Services",
        "license_note": "Check NASA GIBS product terms before redistribution or caching.",
        "layers": layers,
        "refresh_policy": (
            "Poll metadata frequently, but request a new tile only when the "
            "source product has a newer acquisition or processing date."
        ),
        "limitation": (
            "Optical imagery can be blocked by cloud cover and does not confirm "
            "a current road closure or newly falling landslide."
        ),
    }
