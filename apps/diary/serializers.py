from rest_framework import serializers

from apps.weather.serializers import ForecastQuerySerializer

from .models import Diary


class DiaryListSerializer(serializers.ModelSerializer):  # 목록조회
    class Meta:
        model = Diary
        fields = ["id", "date", "title"]


class DiaryDetailSerializer(serializers.ModelSerializer):  # 상세조회
    weather = ForecastQuerySerializer(source="weather_data", read_only=True)

    class Meta:
        model = Diary
        fields = [
            "id",
            "date",
            "title",
            "satisfaction",
            "notes",
            "image_url",
            "weather",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["created_at", "updated_at"]


class DiaryCreateSerializer(serializers.ModelSerializer):
    lat =serializers.FloatField(write_only=True, required=True)
    lon =serializers.FloatField(write_only=True, required=True)
    class Meta:
        model = Diary
        fields = ["date", "title", "satisfaction", "notes", "image_url", "lat", "lon"]

    def create(self, validated_data):
        validated_data.pop("lat", None)
        validated_data.pop("lon", None)
        return super().create(validated_data)
        # lat/lon은 DB 필드 아님 → 제거

class DiaryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diary
        fields = [
            "title",
            "satisfaction",
            "notes",
            "image_url",
            "weather_data",
        ]  # date 제외

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
