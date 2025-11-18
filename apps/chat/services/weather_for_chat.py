from typing import Any, Dict, Optional

from apps.weather.models import WeatherLocation
from apps.weather.services import openweather as ow


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


def get_weather_for_chat(user) -> Optional[Dict[str, Any]]:
    loc = get_user_base_location(user)
    if loc is None:
        return None

    lat = loc.lat
    lon = loc.lon
    cur = ow.get_current(lat=lat, lon=lon)

    return {
        "city": getattr(loc, "dp_name", f"{loc.city} {loc.district}"),
        "temperature": cur["temperature"],
        "feels_like": cur["feels_like"],
        "humidity": cur["humidity"],
        "condition": cur["condition"],
        "rain_probability": cur.get("rain_probability") or 0,
    }
