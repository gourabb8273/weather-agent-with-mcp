"""Weather API: geocode city → NWS points → forecast. Returns JSON."""
import json
from typing import Any

import httpx

NWS_HEADERS = {"User-Agent": "(WeatherAgent, contact@example.com)", "Accept": "application/json"}
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NWS_POINTS_URL = "https://api.weather.gov/points"


def _geocode(city: str) -> tuple[float, float] | None:
    address = city.strip()
    if not address:
        return None
    try:
        r = httpx.get(NOMINATIM_URL, params={"q": address, "format": "json", "limit": 1},
                      headers={"User-Agent": "WeatherAgent/1.0"}, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        lat, lon = data[0].get("lat"), data[0].get("lon")
        return (float(lat), float(lon)) if lat is not None and lon is not None else None
    except Exception:
        return None


def _nws_points(lat: float, lon: float) -> dict[str, Any] | None:
    lat, lon = round(lat, 4), round(lon, 4)
    try:
        r = httpx.get(f"{NWS_POINTS_URL}/{lat},{lon}", headers=NWS_HEADERS, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _nws_forecast(url: str) -> dict[str, Any] | None:
    if not url:
        return None
    try:
        r = httpx.get(url, headers=NWS_HEADERS, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _f_to_c(f: int | float | None) -> int | None:
    if f is None:
        return None
    return round((float(f) - 32) * 5 / 9)


def _parse_forecast(forecast_json: dict[str, Any], city: str) -> dict[str, Any]:
    props = forecast_json.get("properties", {})
    periods = props.get("periods", [])
    current = next((p for p in periods if p.get("isDaytime", True)), periods[0] if periods else None)
    loc = props.get("relativeLocation", {}).get("properties", {}) or {}
    location_name = ", ".join(filter(None, (loc.get("city", city), loc.get("state", ""))))

    result = {"location": location_name or city, "updated": props.get("updateTime"), "current": None, "periods": []}
    if current:
        tf = current.get("temperature")
        result["current"] = {
            "name": current.get("name"), "temperature": tf, "temperatureCelsius": _f_to_c(tf),
            "temperatureUnit": current.get("temperatureUnit", "F"),
            "windSpeed": current.get("windSpeed"), "windDirection": current.get("windDirection"),
            "shortForecast": current.get("shortForecast"), "detailedForecast": current.get("detailedForecast"),
        }
    for p in periods[:4]:
        tf = p.get("temperature")
        result["periods"].append({
            "name": p.get("name"), "temperature": tf, "temperatureCelsius": _f_to_c(tf),
            "temperatureUnit": p.get("temperatureUnit", "F"), "shortForecast": p.get("shortForecast"),
        })
    return result


def get_weather(city: str) -> str:
    """Fetch weather for a city. Returns JSON string."""
    if not city or not str(city).strip():
        return json.dumps({"error": "City name is required."})
    city = str(city).strip()
    coords = _geocode(city)
    if not coords:
        return json.dumps({"error": f"Could not find coordinates for city: {city}"})
    points = _nws_points(*coords)
    if not points:
        return json.dumps({"error": "api.weather.gov points request failed."})
    forecast_url = points.get("properties", {}).get("forecast")
    if not forecast_url:
        return json.dumps({"error": "No forecast URL in api.weather.gov response."})
    forecast = _nws_forecast(forecast_url)
    if not forecast:
        return json.dumps({"error": "Failed to fetch forecast from api.weather.gov."})
    return json.dumps(_parse_forecast(forecast, city), indent=2)
