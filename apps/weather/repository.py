from datetime import datetime, timezone
from typing import Any, Dict

from django.db import transaction

from apps.weather.models import WeatherData, WeatherLocation


def _ts_to_dt_utc(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


@transaction.atomic
def save_current(location: WeatherLocation, current: Dict[str, Any]) -> WeatherData:
    vt = _ts_to_dt_utc(current["base_time"])
    obj, _ = WeatherData.objects.update_or_create(
        location=location,
        valid_time=vt,
        defaults={
            "base_time": vt,
            "temperature": current["temperature"],
            "feels_like": current["feels_like"],
            "humidity": current["humidity"],
            "rain_probability": None,
            "rain_volume": current.get("rain_volume") or None,
            "wind_speed": current.get("wind_speed") or None,
            "condition": current.get("condition"),
            "icon": current.get("icon"),
            "raw_payload": current["raw"],
        },
    )
    return obj


@transaction.atomic
def save_forecast(location: WeatherLocation, forecast_payload: Dict[str, Any]) -> int:
    cnt = 0
    for item in forecast_payload.get("list", []):
        dt = _ts_to_dt_utc(int(item.get("dt", 0)))
        main = item.get("main", {})
        weather0 = (item.get("weather") or [{}])[0]
        wind = item.get("wind", {})
        pop = item.get("pop")  # 0~1, 확률
        rain = item.get("rain", {}) or {}
        defaults = {
            "base_time": dt,
            "temperature": float(main.get("temp")),
            "feels_like": float(main.get("feels_like")),
            "humidity": int(main["humidity"]) if "humidity" in main else None,
            "rain_probability": float(pop) * 100 if pop is not None else None,
            "rain_volume": float(rain.get("3h") or rain.get("1h") or 0.0),
            "wind_speed": float(wind["speed"]) if "speed" in wind else None,
            "condition": weather0.get("main"),
            "icon": weather0.get("icon"),
            "raw_payload": item,
        }
        WeatherData.objects.update_or_create(
            location=location, valid_time=dt, defaults=defaults
        )
        cnt += 1
    return cnt
