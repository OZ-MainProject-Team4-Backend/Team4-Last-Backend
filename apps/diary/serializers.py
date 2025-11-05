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
    class Meta:
        model = Diary
        fields = ["date", "title", "satisfaction", "notes", "image_url", "weather_data"]

    def create(self, validated_data):
        user = self.context["request"].user
        return Diary.objects.create(user=user, **validated_data)


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
