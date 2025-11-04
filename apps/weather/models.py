from django.db import models
from django.utils import timezone

from apps import locations


class WeatherData(models.Model):
    id = models.BigAutoField(primary_key=True)  # Weather_id
    location_id = models.ForeignKey(
        locations.location,
        on_delete=models.CASCADE,
        related_name="weather_data",
    )  # Location_id FK
    base_time = models.DateTimeField()  # API 기준 시각
    valid_time = models.DateTimeField()  # 실제 유호 시각 ( 예보 적용 시점 )
    temperature = models.FloatField()  # 현재 기온 ( °C )
    feels_like = models.FloatField()  # 체감 온도 ( °C )
    humidity = models.IntegerField()  # 습도 ( % )
    rain_probability = models.FloatField()  # 강수 확률 ( % )
    rain_volume = models.FloatField()  # 강수량 ( mm )
    wind_speed = models.FloatField()  # 풍속 ( m/s )
    condition = models.CharField(
        max_length=100
    )  # 날씨 상태 ( "Clear" , "Rain", "Snow" )

    icon = models.CharField(max_length=100)  # 날씨 아이콘 코드
    # icon CharField 적용시 max_length 는 10자로 해도 충분할듯함

    raw_payload = models.JSONField()  # 원본 API 응답 저장용 ( 디버깅 / 백업용 )
    created_at = models.DateTimeField(default=timezone.now)  # 데이터 저장 시각

    class Meta:
        db_table = "weather_data"  # 실제 DB 에 저장될 이름
        Indexes = [
            models.Index(fields=["base_time"]),
            models.Index(fields=["valid_time"]),
        ]

    def __str__(self):
        return f"{self.location_id} - {self.valid_time.strftime("%Y-%m-%d %H:%M")}"
