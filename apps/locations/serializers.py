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
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_is_default(self, value):
        """사용자당 기본 위치는 하나만 허용 (soft delete 제외)"""
        user = self.context["request"].user
        if (
            value
            and FavoriteLocation.objects.filter(
                user=user, is_default=True, deleted_at__isnull=True
            ).exists()
        ):
            raise serializers.ValidationError("이미 기본 위치가 설정되어 있습니다.")
        return value
