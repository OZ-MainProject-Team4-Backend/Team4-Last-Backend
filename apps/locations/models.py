from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import SoftDeleteModel


class Location(models.Model):
    """
    시·도 및 구 단위 지역 정보 테이블
    """

    id = models.BigAutoField(primary_key=True)
    city = models.CharField(max_length=50)  # 시·도 이름 (예: 서울특별시)
    district = models.CharField(max_length=50)  # 구 단위 행정구역 (예: 강남구)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)  # 위도
    longitude = models.DecimalField(max_digits=10, decimal_places=7)  # 경도
    is_active = models.BooleanField(default=True)  # 활성 지역 여부 (default: True)
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시각
    updated_at = models.DateTimeField(auto_now=True)  # 수정 시각

    class Meta:
        db_table = "locations"
        constraints = [
            models.UniqueConstraint(
                fields=["city", "district"],  # 시/구 조합 중복 불가
                name="uq_city_district",  # 제약 조건 이름
            ),
        ]
        indexes = [
            models.Index(
                fields=["latitude", "longitude"]
            ),  # 좌표 검색 성능 향상용 인덱스
        ]
        verbose_name = "지역"
        verbose_name_plural = "지역 목록"

    def __str__(self):
        return f"{self.city} {self.district}"


class FavoriteLocation(SoftDeleteModel):
    """
    사용자별 즐겨찾기 지역 관리 테이블
    SoftDeleteModel 상속 - deleted_at, delete(), hard_delete() 자동 포함
    """

    # id, deleted_at, objects, all_objects는 SoftDeleteModel에서 상속

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # FK - users.id
        on_delete=models.CASCADE,  # 유저 삭제 시 함께 삭제
        related_name="favorite_locations",  # user.favorite_locations 로 접근 가능
        db_index=True,  # 검색 최적화를 위한 인덱스 생성
    )
    location = models.ForeignKey(
        Location,  # FK - locations.id
        on_delete=models.CASCADE,  # Location 삭제 시 함께 삭제
        related_name="favorites",  # location.favorites 로 접근 가능
        db_index=True,  # 인덱스 추가
    )
    alias = models.CharField(
        max_length=100, blank=True, null=True
    )  # 별칭 (집, 회사 등, 선택적)
    is_default = models.BooleanField(default=False)  # 기본 위치 여부 (기본값: False)
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시각
    updated_at = models.DateTimeField(auto_now=True)  # 수정 시각

    class Meta:
        db_table = "favorite_locations"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "location"],  # 같은 유저가 동일한 지역을 중복 등록 불가
                condition=Q(deleted_at__isnull=True),
                name="uq_favorite_user_location",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True, deleted_at__isnull=True),
                name="uq_default_favorite_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_default"]),  # 기본 위치 빠른 조회용 인덱스
        ]
        verbose_name = "즐겨찾기 위치"
        verbose_name_plural = "즐겨찾기 위치 목록"

    def __str__(self):
        base = f"{self.user_id} - {self.location}"
        return f"{base} ({self.alias})" if self.alias else base
