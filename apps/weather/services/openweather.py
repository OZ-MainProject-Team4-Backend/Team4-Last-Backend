import requests
from typing import TypedDict, Dict, Any
from django.conf import settings


class ProviderError(Exception): ...
class ProviderTimeout(Exception): ...

class CurrentOut(TypedDict):
    base_time: int
    temperature: float
    feels_like: float
    humidity: int | None
    wind_speed: float | None
    rain_volume: float | None
    condition: str | None
    icon: str | None
    raw: Dict[str, Any]

def _request(path: str, params: Dict[str, Any], timeout: int | None = None) -> Dict[str, Any]:
    base = settings.OPENWEATHER["BASE_URL"]
    api_key = settings.OPENWEATHER["API_KEY"]
    timeout = timeout or settings.OPENWEATHER.get("TIMEOUT", 5)
    p = {"appid": api_key, "utils": "metric", "lang": "kr", **params}
    try:
        r = requests.get(f"{base}{path}", params=p, timeout=timeout)
        if r.status_code >= 500:
            raise ProviderError("provider_XXX")
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        raise ProviderTimeout()
    except requests.RequestException as e:
        raise ProviderError(str(e))

def get_current(lat: float, lon: float, * , timeout: int | None = None) -> CurrentOut:
    data = _request("/data/2.5/weather", {"lat" : lat, "lon" : lon}, timeout)
    main = data.get("main", {})
    weather0 = (data.get("weather") or [{}])[0]
    wind = data.get("wind", {})
    rain = data.get("rain", {}) or {}
    return {
        "base_time" : int(data.get("dt") or 0),
        "temperature" : float(main.get("temp")),
        "feels_like" : float(main.get("feels_like")),
        "humidity" : int(main["humidity"]) if "humidity" in main else None,
        "wind_speed" : float(wind["speed"]) if "wind_speed" in wind else None,
        "rain_volume" : float(rain.get("1h") or rain.get("3h") or 0.0),
        "condition" : weather0.get("main"),
        "icon" : weather0.get("icon"),
        "raw" : data,
    }

def get_forecast(lat: float, lon: float, *, timeout: int | None = None) -> Dict[str, Any]:
    return _request("/data/2.5/forecast", {"lat" : lat, "lon": lon}, timeout)



