from rest_framework import serializers

from .models import FavoriteLocation, Location


class LocationSerializer(serializers.ModelSerializer):
    """위치 모델 직렬화(조회용)"""

    class Meta:
        model = Location
        fields = ["id", "city", "district", "latitude", "longitude", "is_active"]
        read_only_fields = ["id", "is_active"]  # 읽기 전용 필드 수정 불가


class FavoriteLocationSerializer(serializers.ModelSerializer):
    """즐겨찾기 모델 직렬화"""

    location = LocationSerializer(read_only=True)

    class Meta:
        model = FavoriteLocation
        fields = [
            "id",
            "user",
            "location",
            "alias",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, value):
        """유효성 검사 한 유저당 기본 위치 1개만 허용"""

        user = self.context["request"].user  # 현재 로그인된 사용자 정보 가져오기

        # 기본 위치로 설정하려는 경우
        if value:
            # 이미 기본 위치가 존재한다면 오류 발생
            if FavoriteLocation.objects.filter(user=user, is_default=True).exists():
                raise serializers.ValidationError("이미 기본 위치가 설정되어 있습니다.")

        return value  # 통과 시 그대로 반환
