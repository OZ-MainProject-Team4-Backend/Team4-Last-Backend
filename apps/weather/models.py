from django.db import models
from django.utils import timezone


class WeatherLocation(models.Model):
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    lat = models.FloatField()
    lon = models.FloatField()
    dp_name = models.CharField(max_length=100)

    class Meta:
        db_table = "weather_location"
        unique_together = ("city", "district")

    def __str__(self):
        return f"{self.city} {self.district}"


class WeatherData(models.Model):
    id = models.BigAutoField(primary_key=True)  # Weather_id
    location = models.ForeignKey(
        WeatherLocation,
        on_delete=models.CASCADE,
        related_name="weather_data",
    )  # Location_id FK
    base_time = models.DateTimeField()  # API 기준 시각
    valid_time = models.DateTimeField()  # 실제 유호 시각 ( 예보 적용 시점 )
    temperature = models.FloatField()  # 현재 기온 ( °C )
    feels_like = models.FloatField()  # 체감 온도 ( °C )
    humidity = models.IntegerField(null=True, blank=True)  # 습도 ( % )
    rain_probability = models.FloatField(null=True, blank=True)  # 강수 확률 ( % )
    rain_volume = models.FloatField(null=True, blank=True)  # 강수량 ( mm )
    wind_speed = models.FloatField(null=True, blank=True)  # 풍속 ( m/s )
    condition = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )  # 날씨 상태 ( "Clear" , "Rain", "Snow" )

    icon = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )  # 날씨 아이콘 코드
    # icon CharField 적용시 max_length 는 10자로 해도 충분할듯함

    raw_payload = models.JSONField(
        default=dict
    )  # 원본 API 응답 저장용 ( 디버깅 / 백업용 )
    created_at = models.DateTimeField(default=timezone.now)  # 데이터 저장 시각

    class Meta:
        db_table = "weather_data"  # 실제 DB 에 저장되는 이름
        constraints = [
            models.UniqueConstraint(
                fields=["location", "valid_time"],
                name="uniq_location_valid_time",
            ),
            models.CheckConstraint(
                check=models.Q(humidity__gte=0) & models.Q(humidity__lte=100),
                name="humidity_range_0_100",
            ),
            models.CheckConstraint(
                check=models.Q(rain_probability__gte=0.0)
                & models.Q(rain_probability__lte=100.0),
                name="rain_prob_range_0_100",
            ),
        ]
        indexes = [
            models.Index(fields=["base_time"], name="idx_weather_base_time"),
            models.Index(fields=["valid_time"], name="idx_weather_valid_time"),
            models.Index(fields=["location", "-valid_time"], name="idx_loc_valid_desc"),
        ]
        ordering = ["-valid_time"]
