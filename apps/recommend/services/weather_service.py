import os
from datetime import datetime
import requests


def get_weather_data(latitude: float, longitude: float) -> dict:
    """
    - OPENWEATHER_API_KEY가 있으면 OpenWeather API 호출
    - 없거나 실패 시 모킹 혹은 fallback 값 반환
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")

    # 실제 API 키가 있으면 OpenWeather 호출
    if api_key:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={latitude}&lon={longitude}&appid={api_key}&units=metric&lang=kr"
        )
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            return {
                "temperature": data["main"]["temp"],
                "feels_like": data["main"].get("feels_like"),
                "humidity": data["main"].get("humidity"),
                "wind_speed": data.get("wind", {}).get("speed"),
                "condition": data["weather"][0]["main"],
                "icon": data["weather"][0].get("icon"),
                "base_time": datetime.fromtimestamp(data["dt"]).isoformat(),
                "provider": "OpenWeather",
                "raw": data,
            }
        except requests.RequestException:
            pass  # fallback으로 이동

    # mock or fallback
    return {
        "temperature": 20.0,
        "condition": "Clear",
        "humidity": 50,
        "wind_speed": 1.2,
        "base_time": datetime.now().isoformat(),
        "provider": "fallback" if api_key else "mock",
    }