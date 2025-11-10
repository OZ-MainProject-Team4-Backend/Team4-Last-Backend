from rest_framework import serializers

from apps.weather.serializers import WeatherDataSerializer

from .models import Diary


class DiaryListSerializer(serializers.ModelSerializer):  # 목록조회
    class Meta:
        model = Diary
        fields = ["id", "date", "title"]


class DiaryDetailSerializer(serializers.ModelSerializer):  # 상세조회
    weather = WeatherDataSerializer(source="weather_data", read_only=True)
    icon = serializers.CharField(source="weather_data.icon", read_only=True)

    class Meta:
        model = Diary
        fields = [
            "id",
            "date",
            "title",
            "emotion",
            "notes",
            "image",
            "weather",
            "icon",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["created_at", "updated_at"]


class DiaryCreateSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(write_only=True, required=True)
    lon = serializers.FloatField(write_only=True, required=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Diary
        fields = ["date", "title", "emotion", "notes", "image", "lat", "lon"]
        # weather_data 말고, lat, lon을 불러와서 자동으로 날씨 데이터를 조회해 연결하기 위해


class DiaryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diary
        fields = [
            "title",
            "emotion",
            "notes",
            "image",
        ]
