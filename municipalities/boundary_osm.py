"""One-off OSM/Nominatim fetch for server-side boundary import (not used by the app)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = 'TauSense-Backend/1.0 (Landkreis Hof; boundary import)'

EMPTY_POLYGON: dict = {'type': 'Polygon', 'coordinates': []}


def boundary_has_coordinates(geo_boundary: dict | None) -> bool:
    if not geo_boundary or not isinstance(geo_boundary, dict):
        return False
    coordinates = geo_boundary.get('coordinates')
    if not isinstance(coordinates, list) or not coordinates:
        return False
    geo_type = (geo_boundary.get('type') or '').lower()
    if geo_type == 'polygon':
        ring = coordinates[0] if coordinates else []
        return isinstance(ring, list) and len(ring) >= 3
    if geo_type == 'multipolygon':
        for polygon in coordinates:
            if not isinstance(polygon, list) or not polygon:
                continue
            ring = polygon[0]
            if isinstance(ring, list) and len(ring) >= 3:
                return True
    return False


def fetch_boundary_geometry(
    municipality_name: str,
    *,
    pause_seconds: float = 1.1,
) -> dict | None:
    """
    Resolve municipality boundary via Nominatim (administrative preferred).
    Returns GeoJSON Geometry (Polygon/MultiPolygon) or None.
    """
    query = f'{municipality_name}, Landkreis Hof, Bayern, Deutschland'
    params = urllib.parse.urlencode(
        {
            'q': query,
            'format': 'jsonv2',
            'polygon_geojson': 1,
            'limit': 5,
            'dedupe': 1,
            'countrycodes': 'de',
        }
    )
    url = f'https://nominatim.openstreetmap.org/search?{params}'
    request = urllib.request.Request(
        url,
        headers={
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        },
    )

    time.sleep(pause_seconds)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None

    if not isinstance(payload, list) or not payload:
        return None

    fallback: dict | None = None
    for candidate in payload:
        if not isinstance(candidate, dict):
            continue
        geojson = candidate.get('geojson')
        if not isinstance(geojson, dict):
            continue
        if not boundary_has_coordinates(geojson):
            continue

        result_class = str(candidate.get('class') or '').lower()
        result_type = str(candidate.get('type') or '').lower()
        if result_class == 'boundary' or result_type == 'administrative':
            return geojson
        if fallback is None:
            fallback = geojson

    return fallback
