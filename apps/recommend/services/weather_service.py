def get_weather_data(latitude: float, longitude: float) -> dict:
    """
    임시
    실제로는 OpenWeather API 등을 호출해서 데이터를 받아올 예정.
    현재는 테스트용으로 임의 값 반환.
    """
    return {
        "temperature": 22.5,  # 임시 기온
        "condition": "Clear",  # 임시 날씨
    }