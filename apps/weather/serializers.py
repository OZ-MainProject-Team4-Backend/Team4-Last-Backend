from rest_framework import serializers

from apps.weather.models import WeatherData


class CurrentQuerySerializer(serializers.Serializer):
    city = serializers.CharField(required=False, allow_blank=True)
    district = serializers.CharField(required=False, allow_blank=True)
    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)

    def validate(self, attrs):
        has_xy = "lat" in attrs and "lon" in attrs
        has_name = bool(attrs.get("city"))
        if not has_xy and not has_name:
            raise serializers.ValidationError("city 또는 lat/lon 중 하나는 필수")
        if ("lat" in attrs) ^ ("lon" in attrs):
            raise serializers.ValidationError("lat과 lon은 함께 전달해야 함")
        return attrs


class ForecastQuerySerializer(CurrentQuerySerializer):
    pass


class HistoryQuerySerializer(serializers.Serializer):
    location_id = serializers.IntegerField(required=False)
    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)

    def validate(self, attrs):
        if not attrs.get("location_id") and not ("lat" in attrs and "lon" in attrs):
            raise serializers.ValidationError("location_id 또는 lat/lon 중 하나는 필수")
        return attrs


class WeatherDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherData
        fields = [
            "id",
            "base_time",
            "valid_time",
            "temperature",
            "feels_like",
            "humidity",
            "rain_probability",
            "rain_volume",
            "wind_speed",
            "condition",
            "icon",
        ]
