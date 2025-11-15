from rest_framework import serializers

from .models import OutfitRecommendation


class CoordsRecommendSerializer(serializers.Serializer):
    """좌표 기반 추천 요청"""

    latitude = serializers.FloatField(help_text="위도")
    longitude = serializers.FloatField(help_text="경도")


class LocationRecommendSerializer(serializers.Serializer):
    """지역 기반 추천 요청"""

    city = serializers.CharField(help_text="도시명 (예: 서울특별시)")
    district = serializers.CharField(help_text="구/군명 (예: 강남구)")


class OutfitRecommendSerializer(serializers.ModelSerializer):
    """복장 추천 응답"""

    recommendations = serializers.SerializerMethodField()

    class Meta:
        model = OutfitRecommendation
        fields = [
            "id",
            "weather_data",
            "recommendations",
            "explanation",
            "image_url",
            "created_at",
        ]

    def get_recommendations(self, obj):
        """rec_1~3을 리스트 형태로 묶어서 반환"""
        return [obj.rec_1, obj.rec_2, obj.rec_3]
