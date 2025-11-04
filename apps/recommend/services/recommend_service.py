from .weather_service import get_weather_data


def generate_outfit_recommend(user, latitude: float, longitude: float) -> dict:
    """
    날씨 데이터를 기반으로 복장을 추천하는 함수 (룰 기반)
    온도와 날씨 상태를 기준으로 추천 코디 3종과 설명문을 생성함
    현재는 하드코딩된 룰 기반임

    Args:
        user: Django User 객체 (비로그인 시 None)
        latitude (float): 위도
        longitude (float): 경도

    Returns:
        dict: {
            "rec_1": str,
            "rec_2": str,
            "rec_3": str,
            "explanation": str
        }
    """

    # 날씨 데이터 가져오기
    weather = get_weather_data(latitude, longitude)
    temp = weather.get("temperature", 20)
    cond = (weather.get("condition") or "Clear").lower()

    rec_1 = rec_2 = rec_3 = explanation = ""

    # 날씨 상태별 추천 (눈, 비)
    if cond in ["snow", "눈"]:
        rec_1, rec_2, rec_3 = (
            "롱패딩 + 니트 + 와이드 슬랙스 + 스니커즈",
            "숏패딩 + 후드집업 + 트레이닝 팬츠 + 운동화",
            "코트 + 목폴라 + 기모 슬랙스 + 부츠",
        )
        explanation = "눈 오는 날엔 방한성과 보온성을 높인 따뜻한 코디를 추천드려요."

    elif cond in ["rain", "비"]:
        rec_1, rec_2, rec_3 = (
            "아노락 집업 + 반바지 + 슬리퍼",
            "통풍형 바람막이 + 반바지 + 레인부츠",
            "반팔티 + 와이드 데님 팬츠 + 단화",
        )
        explanation = "비 오는 날엔 방수 소재와 통풍이 잘 되는 코디를 추천드려요."

    # 온도 기준 세분화
    elif temp <= -5:
        rec_1, rec_2, rec_3 = (
            "롱패딩 + 히트텍 + 맨투맨 + 기모 슬랙스 + 어그 슈즈 + 머플러",
            "패딩 + 니트 + 코듀로이 팬츠 + 방한 부츠",
            "다운점퍼 + 후드 + 카고팬츠 + 스니커즈 + 장갑",
        )
        explanation = f"{temp}°C의 혹한기에는 완전 방한 코디가 필수예요."

    elif temp <= 0:
        rec_1, rec_2, rec_3 = (
            "롱패딩 + 플리스 집업 + 기모 팬츠 + 스니커즈",
            "숏패딩 + 기모 후드티 + 카고 팬츠 + 어그 슈즈 + 장갑",
            "울 코트 + 니트 + 울 팬츠 + 부츠 + 머플러 ",
        )
        explanation = f"{temp}°C 이하의 한파에는 보온성 있는 코디를 추천드려요."

    elif temp <= 5:
        rec_1, rec_2, rec_3 = (
            "숏패딩 + 맨투맨 + 조거 팬츠 + 운동화",
            "롱 코트 + 니트 + 데님 팬츠 + 더비 슈즈",
            "롱 파카 + 후드집업 + 트레이닝팬츠 + 운동화",
        )
        explanation = f"{temp}°C에는 두꺼운 아우터와 레이어드 코디를 추천드려요."

    elif temp <= 9:
        rec_1, rec_2, rec_3 = (
            "패딩 자켓 + 후드티 + 와이드 진 + 더비 슈즈",
            "발마칸 코트 + 니트 + 와이드 진 + 운동화",
            "피쉬테일 롱 패딩 + 기모 트레이닝 팬츠 + 어그 슈즈",
        )
        explanation = (
            f"{temp}°C에는 아직 쌀쌀하니 두께감 있는 자켓이나 코트를 추천드려요."
        )

    elif temp <= 11:
        rec_1, rec_2, rec_3 = (
            "코듀로이 자켓 + 목폴라 니트 + 세미 와이드 데님 팬츠 + 더비 슈즈",
            "발마칸 코트 + 라운드 니트 + 와이드 데님 팬츠 + 스웨이드 슈즈",
            "숏패딩 + 기모 후드티 + 트레이닝 팬츠 + 운동화",
        )
        explanation = f"{temp}°C에는 두께감 있는 자켓이나 코트를 추천드려요."

    elif temp <= 17:
        rec_1, rec_2, rec_3 = (
            "레더 자켓 + 니트 + 세미 와이드 데님 팬츠 + 더비 슈즈",
            "니트 가디건 + 긴팔티 + 와이드 슬랙스 + 운동화",
            "기모 후드티 + 반팔 + 트레이닝 팬츠 + 운동화",
        )
        explanation = f"{temp}°C엔 간절기용 겉옷을 챙기세요."

    elif temp <= 21:
        rec_1, rec_2, rec_3 = (
            "블루종 + 니트 + 와이드 데님 팬츠 + 첼시 부츠",
            "크롭 니트 가디건 + 니트 + 와이드 슬랙스 + 더비 슈즈",
            "얇은 가디건 + 반팔 + 코튼팬츠 + 단화",
        )
        explanation = f"{temp}°C엔 가벼운 아우터 코디를 추천드려요."

    elif temp <= 25:
        rec_1, rec_2, rec_3 = (
            "반팔티 + 와이드 팬츠 + 스니커즈",
            "린넨 셔츠 + 슬랙스 + 샌들",
            "롱 슬리브 + 데님 반바지 + 운동화 + 크로스백",
        )
        explanation = f"{temp}°C엔 가벼운 코디가 좋아요."

    elif temp <= 29:
        rec_1, rec_2, rec_3 = (
            "반팔티 + 반바지 + 슬리퍼",
            "반팔티 + 린넨팬츠 + 샌들",
            "린넨 셔츠 + 와이드 데님 팬츠 + 슬리퍼",
        )
        explanation = f"{temp}°C엔 통풍이 잘 되는 옷을 입어주세요."

    else:
        rec_1, rec_2, rec_3 = (
            "민소매 + 린넨 팬츠 + 슬리퍼 + 선글라스",
            "반팔 + 반바지 + 슬리퍼",
            "린넨 셔츠 + 반바지 + 샌들",
        )
        explanation = f"{temp}°C 이상의 무더운 날씨엔 시원한 소재의 옷을 추천드려요."

    # 딕셔너리 형태로 반환
    return {
        "rec_1": rec_1,
        "rec_2": rec_2,
        "rec_3": rec_3,
        "explanation": explanation,
    }
