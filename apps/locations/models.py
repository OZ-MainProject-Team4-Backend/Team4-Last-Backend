from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class FavoriteLocation(SoftDeleteModel):
    """
    사용자별 즐겨찾기 지역 관리 (weather의 Location과 분리)
    - FK → users.id (user)
    - city, district: 문자열로 저장 (그럼 이것도 weather에서 받아야할듯?)
    - alias: 별칭 (집, 회사 등)
    - is_default: 사용자 기본 위치 여부 (한 명당 1개만 True)
    - SoftDeleteModel: deleted_at 필드 및 soft delete 동작 포함
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_locations",
        db_index=True,
    )
    alias = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    city = models.CharField(max_length=50)  # 시/도 (예: 서울시)
    district = models.CharField(max_length=50)  # 구 (예: 강남구)
    is_default = models.BooleanField(default=False)  # 기본 위치 여부 (1개만 True 가능)
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시각
    updated_at = models.DateTimeField(auto_now=True)  # 수정 시각

    class Meta:
        db_table = "favorite_locations"
        constraints = [
            # 동일 사용자 + 동일 지역 중복 방지 (soft delete 제외)
            models.UniqueConstraint(
                fields=["user", "city", "district"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_favorite_user_city_district",
            ),
            # 사용자당 기본 위치는 하나만 True 가능
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True, deleted_at__isnull=True),
                name="uq_default_favorite_per_user",
            ),
        ]
        indexes = [models.Index(fields=["user", "is_default"])]
        verbose_name = "즐겨찾기 위치"
        verbose_name_plural = "즐겨찾기 위치 목록"

    def __str__(self):
        return f"{self.user_id} - {self.city} {self.district} ({self.alias or ''})"
