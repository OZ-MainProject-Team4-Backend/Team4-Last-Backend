from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class FavoriteLocation(SoftDeleteModel):
    """
    사용자 별 즐겨찾기 지역 관리
    사용자 별 즐겨찾기 노출 순서를 order 필드로 관리
    한 사용자당 즐겨찾기 3개까지 가능
    order : 낮을수록 상단에 표시(0, 1, 2)
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
    order = models.PositiveIntegerField(default=0) # 즐겨찾기 순서
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시각
    updated_at = models.DateTimeField(auto_now=True)  # 수정 시각

    class Meta:
        db_table = "favorite_locations"

        constraints = [
            # 동일 사용자 + 동일 지역 중복 방지 (soft delete 제외)
            models.UniqueConstraint(
                fields=["user", "city", "district"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_favorite_unique_location_per_user",
            ),
        ]

        indexes = [
            models.Index(fields=["user", "order"]),
        ]

        ordering = ["order"]

    def __str__(self):
        return f"{self.user_id} - {self.alias or ''} ({self.city} {self.district})"
