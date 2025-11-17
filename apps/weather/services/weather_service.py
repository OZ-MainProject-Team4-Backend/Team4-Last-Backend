from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from apps.weather.services import openweather


class CurrentOut(openweather.CurrentOut, total=False):
    """openweather.CurrentOut 확장형 — valid_time 키 추가"""

    valid_time: float


def get_current(lat: float, lon: float) -> CurrentOut:
    data: CurrentOut = openweather.get_current(lat, lon)  # type: ignore[assignment]

    # valid_time이 없으면 base_time 기준으로 추가
    if "valid_time" not in data:
        base_time = data.get("base_time", datetime.now().timestamp())
        data["valid_time"] = base_time

    return data
