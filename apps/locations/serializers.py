from rest_framework import serializers
from django.db import models
from .models import FavoriteLocation


class FavoriteLocationSerializer(serializers.ModelSerializer):
    """즐겨찾기 지역 직렬화"""

    class Meta:
        model = FavoriteLocation
        fields = [
            "id",
            "alias",
            "city",
            "district",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "order", "created_at", "updated_at"]

    def validate(self, attrs):
        """사용자당 최대 3개의 즐겨찾기 제한"""
        user = self.context["request"].user
        count = FavoriteLocation.objects.filter(user=user, deleted_at__isnull=True).count()

        # create 시에만 제한 확인
        if self.instance is None and count >= 3:
            raise serializers.ValidationError("즐겨찾기는 최대 3개까지 등록할 수 있습니다.")
        return attrs

    def create(self, validated_data):
        """새로 생성 시 order 값 자동 부여 (0, 1, 2 순서)"""
        user = self.context["request"].user

        max_order = (
            FavoriteLocation.objects.filter(user=user, deleted_at__isnull=True)
            .aggregate(models.Max("order"))
            .get("order__max")
        )

        validated_data["order"] = (max_order or 0) + 1
        return super().create(validated_data)
