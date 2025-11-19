from typing import Any, Dict, Optional

from apps.weather.models import WeatherLocation
from apps.weather.services import geocoding
from apps.weather.services import openweather as ow
from apps.weather.services.openweather import CurrentOut


def get_user_base_location(user) -> Optional[WeatherLocation]:
    if user is None or not user.is_authenticated:
        return None

    if hasattr(user, "default_location") and user.default_location:
        return user.default_location

    if hasattr(user, "favorite_locations"):
        fav = user.favorite_locations.first()
        if fav and getattr(fav, "location", None):
            return fav.location

    return None


def get_weather_for_chat(
    user=None,
    *,
    lat: float | None = None,
    lon: float | None = None,
    city: str | None = None,
    district: str | None = None,
) -> Optional[Dict[str, Any]]:

    if lat is not None and lon is not None:
        cur: CurrentOut = ow.get_current(lat=lat, lon=lon)

        parts = [p for p in [city, district] if p]
        city_name = " ".join(parts) or "현재 위치"

        return {
            "city": city_name,
            "temperature": cur["temperature"],
            "feels_like": cur["feels_like"],
            "humidity": cur["humidity"],
            "condition": cur["condition"],
            "rain_probability": cur.get("rain_volume")
            or cur.get("rain_probability")
            or 0,
        }

    loc = get_user_base_location(user)
    if loc is None:
        return None

    cur2: CurrentOut = ow.get_current(lat=loc.lat, lon=loc.lon)

    return {
        "city": getattr(loc, "dp_name", f"{loc.city} {loc.district}"),
        "temperature": cur2["temperature"],
        "feels_like": cur2["feels_like"],
        "humidity": cur2["humidity"],
        "condition": cur2["condition"],
        "rain_probability": cur2.get("rain_volume")
        or cur2.get("rain_probability")
        or 0,
    }


#
