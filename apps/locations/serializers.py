from django.db import IntegrityError, transaction
from rest_framework import serializers

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

    @transaction.atomic
    def create(self, validated_data):
        """동시성 안전한 order 배정 + 3개 제한 + 중복 예외 처리"""
        user = self.context["request"].user
        validated_data["user"] = user

        qs = FavoriteLocation.objects.select_for_update().filter(
            user=user,
            deleted_at__isnull=True,
        )

        # 최대 3개 제한
        if qs.count() >= 3:
            raise serializers.ValidationError(
                {
                    "error": "limit_exceeded",
                    "message": "즐겨찾기는 최대 3개까지 등록 가능합니다.",
                }
            )

        # 비어있는 오더에 자동 배정
        existing_orders = set(qs.values_list("order", flat=True))
        for i in range(3):
            if i not in existing_orders:
                validated_data["order"] = i
                break

        # 지역 중복 처리 - already_exists
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {
                    "error": "already_exists",
                    "message": "이미 즐겨찾기에 등록된 지역입니다.",
                }
            )
