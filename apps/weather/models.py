from django.db import models


class Location(models.Model):
    city = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    class Meta:
        db_table = "weather_locations"


class WeatherData(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    # 나머지 weather 데이터…
