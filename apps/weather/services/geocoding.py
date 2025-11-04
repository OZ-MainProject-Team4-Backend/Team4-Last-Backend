import requests
from django.conf import settings


class GeocodingError(Exception):
    pass


def build_query(city: str, district: str | None, country_code: str = "KR") -> str:
    city_n = city
    district_n = district or ""
    parts = [p for p in [district_n, city_n, country_code] if p]
    return ",".join(parts)


def geocode_city_district(
    city: str, district: str | None = None, *, timeout: int | None = None
):
    base = settings.OPENWEATHER["BASE_URL"]
    api_key = settings.OPENWEATHER["API_KEY"]
    timeout = timeout or settings.OPENWEATHER.get("TIMEOUT", 5)

    q = build_query(city, district, "KR")
    url = f"{base}/geo/1.0/direct"
    params = {"q": q, "limit": 1, "appid": api_key}

    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code >= 500:
            raise GeocodingError("provider_error")
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        item = data[0]
        return {
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "city": item.get("name") or city,
            "district": district,
            "country_code": (item.get("country") or "KR"),
        }
    except requests.exceptions.Timeout:
        raise GeocodingError("timeout")
    except requests.RequestException:
        raise GeocodingError("request_failed")
