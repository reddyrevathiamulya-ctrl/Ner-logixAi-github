from __future__ import annotations

from typing import Any


SOURCE_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "id": "openstreetmap",
        "feature": "roads_and_basemap",
        "provider": "OpenStreetMap",
        "access": "open data",
        "update_behavior": "community updates; not guaranteed real-time",
        "best_for": "road geometry, names, surfaces, map context",
        "limitation": "temporary closures may be missing",
    },
    {
        "id": "osrm",
        "feature": "route_geometry",
        "provider": "OSRM",
        "access": "open-source routing engine",
        "update_behavior": "depends on road graph updates",
        "best_for": "driving route geometry, distance, duration",
        "limitation": "does not provide authoritative live road closure status",
    },
    {
        "id": "open_meteo",
        "feature": "weather_and_forecast",
        "provider": "Open-Meteo",
        "access": "free API",
        "update_behavior": "forecast model dependent; polled continuously",
        "best_for": "current weather, rain, wind, forecast",
        "limitation": "model data is not a field observation",
    },
    {
        "id": "nasa_gpm_imerg",
        "feature": "high_frequency_rainfall",
        "provider": "NASA GPM IMERG",
        "access": "open NASA Earthdata product; access terms apply",
        "update_behavior": "near-real-time products with processing latency",
        "best_for": "rainfall accumulation and storm triggers",
        "limitation": "not direct road or landslide observation",
    },
    {
        "id": "nasa_gibs",
        "feature": "satellite_map_layers",
        "provider": "NASA Global Imagery Browse Services",
        "access": "open imagery service; product terms apply",
        "update_behavior": "daily or product dependent, cloud dependent",
        "best_for": "visual regional context and broad change screening",
        "limitation": "does not confirm a live road closure or boulder",
    },
    {
        "id": "sentinel_1",
        "feature": "radar_change_detection",
        "provider": "Copernicus Sentinel-1",
        "access": "open data via Copernicus Data Space",
        "update_behavior": "revisit and processing dependent",
        "best_for": "cloud-resistant flood and surface-change analysis",
        "limitation": "requires raster processing; not continuous imagery",
    },
    {
        "id": "copernicus_dem",
        "feature": "rockfall_terrain_susceptibility",
        "provider": "Copernicus DEM / OpenTopography",
        "access": "open elevation products; terms vary by product",
        "update_behavior": "static terrain model",
        "best_for": "slope, relief, drainage, terrain roughness proxies",
        "limitation": "cannot identify a specific loose boulder or joint",
    },
    {
        "id": "local_geology_and_drones",
        "feature": "individual_boulder_assessment",
        "provider": "Geological Survey / surveyed field or UAV imagery",
        "access": "requires authorized local data collection",
        "update_behavior": "survey dependent",
        "best_for": "rock type, joints, cracks, detached blocks, road-cut inspection",
        "limitation": "not available as a universal free live feed",
    },
    {
        "id": "nasa_landslide_catalog",
        "feature": "historical_landslides",
        "provider": "NASA Global Landslide Catalog",
        "access": "open historical dataset",
        "update_behavior": "historical catalog, not live feed",
        "best_for": "susceptibility evidence and model training",
        "limitation": "does not confirm current events",
    },
    {
        "id": "field_reports",
        "feature": "current_ground_truth",
        "provider": "NER-LogixAI field users",
        "access": "first-party reports",
        "update_behavior": "on submission; verification dependent",
        "best_for": "blocked roads, damage, floods, local incidents",
        "limitation": "coverage and accuracy depend on reporters",
    },
)


def get_source_registry() -> dict[str, Any]:
    return {
        "sources": list(SOURCE_REGISTRY),
        "principle": (
            "A risk estimate is never a confirmed closure unless current, "
            "verified ground evidence supports it."
        ),
    }
