from rest_framework import serializers

from .models import OutfitRecommendation


class OutfitRecommendSerializer(serializers.ModelSerializer):
    # rec_1, rec_2, rec_3 > 하나의 리스트로 반환
    recommendations = serializers.SerializerMethodField()

    class Meta:
        model = OutfitRecommendation
        fields = [
            "id",
            "recommendations",
            "explanation",
            "image_url",
            "created_at",
        ]

    def get_recommendations(self, obj):

        # 세 개의 복장 추천 필드를 하나의 리스트로 묶어 반환.
        return [obj.rec_1, obj.rec_2, obj.rec_3]
