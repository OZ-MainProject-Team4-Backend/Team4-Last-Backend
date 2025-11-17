from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Tuple, cast

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from apps.recommend.models import OutfitRecommendation
from apps.weather.models import WeatherData, WeatherLocation
from apps.weather.services.weather_service import get_current

User: Any = get_user_model()


def _recommend_by_condition(
    cond: str,
) -> Tuple[Tuple[str, str, str], str] | Tuple[None, None]:
    cond = cond.lower()
    if cond in ["snow", "눈"]:
        return (
            (
                "롱패딩 + 니트 + 와이드 슬랙스 + 스니커즈",
                "숏패딩 + 후드집업 + 트레이닝 팬츠 + 운동화",
                "코트 + 목폴라 + 기모 슬랙스 + 부츠",
            ),
            "눈 오는 날엔 방한성과 보온성을 높인 따뜻한 코디를 추천드려요.",
        )
    if cond in ["rain", "비"]:
        return (
            (
                "아노락 집업 + 반바지 + 슬리퍼",
                "통풍형 바람막이 + 반바지 + 레인부츠",
                "반팔티 + 와이드 데님 팬츠 + 단화",
            ),
            "비 오는 날엔 방수 소재와 통풍이 잘 되는 코디를 추천드려요.",
        )
    return None, None


def _recommend_by_temperature(temp: float) -> Tuple[Tuple[str, str, str], str]:
    if temp <= -5:
        return (
            (
                "롱패딩 + 히트텍 + 맨투맨 + 기모 슬랙스 + 어그 슈즈 + 머플러",
                "패딩 + 니트 + 코듀로이 팬츠 + 방한 부츠",
                "다운점퍼 + 후드 + 카고팬츠 + 스니커즈 + 장갑",
            ),
            f"{temp}°C의 혹한기에는 완전 방한 코디가 필수예요.",
        )
    if temp <= 0:
        return (
            (
                "롱패딩 + 플리스 집업 + 기모 팬츠 + 스니커즈",
                "숏패딩 + 기모 후드티 + 카고 팬츠 + 어그 슈즈 + 장갑",
                "울 코트 + 니트 + 울 팬츠 + 부츠 + 머플러 ",
            ),
            f"{temp}°C 이하의 한파에는 보온성 있는 코디를 추천드려요.",
        )
    if temp <= 5:
        return (
            (
                "숏패딩 + 맨투맨 + 조거 팬츠 + 운동화",
                "롱 코트 + 니트 + 데님 팬츠 + 더비 슈즈",
                "롱 파카 + 후드집업 + 트레이닝팬츠 + 운동화",
            ),
            f"{temp}°C에는 두꺼운 아우터와 레이어드 코디를 추천드려요.",
        )
    if temp <= 25:
        return (
            (
                "반팔티 + 와이드 팬츠 + 스니커즈",
                "린넨 셔츠 + 슬랙스 + 샌들",
                "롱 슬리브 + 데님 반바지 + 운동화 + 크로스백",
            ),
            f"{temp}°C엔 가벼운 코디가 좋아요.",
        )
    return (
        (
            "민소매 + 린넨 팬츠 + 슬리퍼 + 선글라스",
            "반팔 + 반바지 + 슬리퍼",
            "린넨 셔츠 + 반바지 + 샌들",
        ),
        f"{temp}°C 이상의 무더운 날씨엔 시원한 소재의 옷을 추천드려요.",
    )


def _save_weather(lat: float, lon: float) -> WeatherData:
    """OpenWeather 데이터를 WeatherData로 저장"""
    w = get_current(lat, lon)

    base_time_raw = w.get("base_time")
    valid_time_raw = w.get("valid_time", base_time_raw)

    base_time = (
        datetime.fromtimestamp(base_time_raw)
        if isinstance(base_time_raw, (int, float))
        else datetime.now()
    )
    valid_time = (
        datetime.fromtimestamp(valid_time_raw)
        if isinstance(valid_time_raw, (int, float))
        else datetime.now()
    )

    return WeatherData.objects.create(
        location=cast(WeatherLocation, None),
        base_time=base_time,
        valid_time=valid_time,
        temperature=w.get("temperature", 0.0),
        feels_like=w.get("feels_like") or 0.0,
        humidity=w.get("humidity") or 0.0,
        rain_probability=None,
        rain_volume=w.get("rain_volume") or 0.0,
        wind_speed=w.get("wind_speed") or 0.0,
        condition=w.get("condition") or "",
        icon=w.get("icon") or "",
        raw_payload=w.get("raw", {}),
    )


def _generate(lat: float, lon: float) -> dict[str, str]:
    weather = get_current(lat, lon)
    temp = weather.get("temperature", 20.0)
    cond = (weather.get("condition") or "Clear").lower()

    recs, explanation = _recommend_by_condition(cond)
    if not recs:
        recs, explanation = _recommend_by_temperature(temp)

    return {
        "rec_1": recs[0],
        "rec_2": recs[1],
        "rec_3": recs[2],
        "explanation": explanation or "",
    }


@transaction.atomic
def create_by_coords(
    user: Optional[Any], lat: float, lon: float
) -> OutfitRecommendation:
    """좌표 기반 추천"""
    data = _generate(lat, lon)
    weather_data = _save_weather(lat, lon)
    user_obj = user if getattr(user, "is_authenticated", False) else None

    return OutfitRecommendation.objects.create(
        user=cast(User, user_obj),  # ✅ Combinable 타입 맞춤
        weather_data=weather_data,
        rec_1=data["rec_1"],
        rec_2=data["rec_2"],
        rec_3=data["rec_3"],
        explanation=data["explanation"],
    )


@transaction.atomic
def create_by_location(
    user: Optional[Any], city: str, district: str
) -> OutfitRecommendation:
    """지역 기반 추천"""
    try:
        loc = WeatherLocation.objects.get(city=city, district=district)
    except ObjectDoesNotExist:
        raise ValueError("해당 지역의 좌표 정보를 찾을 수 없습니다.")

    data = _generate(loc.lat, loc.lon)
    weather_data = _save_weather(loc.lat, loc.lon)
    weather_data.location = loc
    weather_data.save(update_fields=["location"])

    user_obj = user if getattr(user, "is_authenticated", False) else None
    return OutfitRecommendation.objects.create(
        user=cast(User, user_obj),
        weather_data=weather_data,
        rec_1=data["rec_1"],
        rec_2=data["rec_2"],
        rec_3=data["rec_3"],
        explanation=data["explanation"],
    )
