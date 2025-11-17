from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from apps.recommend.models import OutfitRecommendation
from apps.weather.models import WeatherData, WeatherLocation
from apps.weather.services.weather_service import CurrentOut, get_current

UserModel = get_user_model()


def _recommend_by_condition(
    cond: str,
) -> Tuple[Tuple[str, str, str], str] | Tuple[None, None]:
    cond = cond.lower()

    # 눈 / 비 우선 처리
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

    if temp <= 9:
        return (
            (
                "패딩 자켓 + 후드티 + 와이드 진 + 더비 슈즈",
                "발마칸 코트 + 니트 + 와이드 진 + 운동화",
                "피쉬테일 롱 패딩 + 기모 트레이닝 팬츠 + 어그 슈즈",
            ),
            f"{temp}°C에는 아직 쌀쌀하니 두께감 있는 자켓이나 코트를 추천드려요.",
        )

    if temp <= 11:
        return (
            (
                "코듀로이 자켓 + 목폴라 니트 + 세미 와이드 데님 팬츠 + 더비 슈즈",
                "발마칸 코트 + 라운드 니트 + 와이드 데님 팬츠 + 스웨이드 슈즈",
                "숏패딩 + 기모 후드티 + 트레이닝 팬츠 + 운동화",
            ),
            f"{temp}°C에는 두께감 있는 자켓이나 코트를 추천드려요.",
        )

    if temp <= 17:
        return (
            (
                "레더 자켓 + 니트 + 세미 와이드 데님 팬츠 + 더비 슈즈",
                "니트 가디건 + 긴팔티 + 와이드 슬랙스 + 운동화",
                "기모 후드티 + 반팔 + 트레이닝 팬츠 + 운동화",
            ),
            f"{temp}°C엔 간절기용 겉옷을 챙기세요.",
        )

    if temp <= 21:
        return (
            (
                "블루종 + 니트 + 와이드 데님 팬츠 + 첼시 부츠",
                "크롭 니트 가디건 + 니트 + 와이드 슬랙스 + 더비 슈즈",
                "얇은 가디건 + 반팔 + 코튼팬츠 + 단화",
            ),
            f"{temp}°C엔 가벼운 아우터 코디를 추천드려요.",
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

    if temp <= 29:
        return (
            (
                "반팔티 + 반바지 + 슬리퍼",
                "반팔티 + 린넨팬츠 + 샌들",
                "린넨 셔츠 + 와이드 데님 팬츠 + 슬리퍼",
            ),
            f"{temp}°C엔 통풍이 잘 되는 옷을 입어주세요.",
        )

    return (
        (
            "민소매 + 린넨 팬츠 + 슬리퍼 + 선글라스",
            "반팔 + 반바지 + 슬리퍼",
            "린넨 셔츠 + 반바지 + 샌들",
        ),
        f"{temp}°C 이상의 무더운 날씨엔 시원한 소재의 옷을 추천드려요.",
    )


def _save_weather(
    lat: float,
    lon: float,
    *,
    location: Optional[WeatherLocation] = None,
) -> WeatherData:
    """OpenWeather 데이터를 WeatherData로 저장"""
    w: CurrentOut = get_current(lat, lon)

    base_time_raw = w.get("base_time")
    valid_time_raw = w.get("valid_time", base_time_raw)

    if isinstance(base_time_raw, (int, float)):
        base_time = datetime.fromtimestamp(base_time_raw)
    else:
        base_time = datetime.now()

    if isinstance(valid_time_raw, (int, float)):
        valid_time = datetime.fromtimestamp(valid_time_raw)
    else:
        valid_time = base_time

    kwargs: Dict[str, Any] = {
        "base_time": base_time,
        "valid_time": valid_time,
        "temperature": float(w.get("temperature", 0.0) or 0.0),
        "feels_like": float(w.get("feels_like", 0.0) or 0.0),
        "humidity": w.get("humidity"),
        "rain_probability": None,
        "rain_volume": w.get("rain_volume"),
        "wind_speed": w.get("wind_speed"),
        "condition": w.get("condition"),
        "icon": w.get("icon"),
        "raw_payload": w.get("raw", {}),
    }
    if location is not None:
        kwargs["location"] = location

    return WeatherData.objects.create(**kwargs)


def _generate(lat: float, lon: float) -> Dict[str, str]:
    """실제 추천 생성 로직 (좌표 → 날씨 → 코디 3개 + 설명)"""
    w = get_current(lat, lon)
    temp = float(w.get("temperature", 20.0) or 20.0)
    cond = (w.get("condition") or "Clear").lower()

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
def create_by_coords(user: Any, lat: float, lon: float) -> OutfitRecommendation:
    """좌표 기반 추천 생성 + 저장"""
    data = _generate(lat, lon)
    weather_data = _save_weather(lat, lon)

    kwargs: Dict[str, Any] = {
        "weather_data": weather_data,
        "rec_1": data["rec_1"],
        "rec_2": data["rec_2"],
        "rec_3": data["rec_3"],
        "explanation": data["explanation"],
    }
    # 사용자 로그인 상태일 때만 user 필드 세팅
    if getattr(user, "is_authenticated", False):
        kwargs["user"] = user

    return OutfitRecommendation.objects.create(**kwargs)


@transaction.atomic
def create_by_location(
    user: Any,
    city: str,
    district: str,
) -> OutfitRecommendation:
    """지역 기반 추천 생성 + 저장"""
    try:
        loc = WeatherLocation.objects.get(city=city, district=district)
    except ObjectDoesNotExist:
        raise ValueError("해당 지역의 좌표 정보를 찾을 수 없습니다.")

    data = _generate(loc.lat, loc.lon)
    weather_data = _save_weather(loc.lat, loc.lon, location=loc)

    kwargs: Dict[str, Any] = {
        "weather_data": weather_data,
        "rec_1": data["rec_1"],
        "rec_2": data["rec_2"],
        "rec_3": data["rec_3"],
        "explanation": data["explanation"],
    }
    if getattr(user, "is_authenticated", False):
        kwargs["user"] = user

    return OutfitRecommendation.objects.create(**kwargs)


def build_outfit_by_temp_and_cond(
    temp: float,
    cond: Optional[str],
) -> Dict[str, str]:
    """AI 챗봇에서 날씨(온도/상태)만 받아 룰 기반 코디를 만드는 함수"""
    recs, explanation = _recommend_by_condition(cond or "")
    if not recs:
        recs, explanation = _recommend_by_temperature(temp)

    return {
        "rec_1": recs[0],
        "rec_2": recs[1],
        "rec_3": recs[2],
        "explanation": explanation or "",
    }


def generate_outfit_recommend(
    user: Any, latitude: float, longitude: float
) -> Dict[str, str]:
    """기존 시그니처 유지용: (user, 위도, 경도) -> 추천 dict"""
    return _generate(latitude, longitude)
