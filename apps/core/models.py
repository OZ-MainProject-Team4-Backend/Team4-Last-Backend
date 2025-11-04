from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """삭제되지 않은 객체만 반환"""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    """soft delete 기능 제공 모델
    실제 삭제 대신 deleted_at 필드에 시간 기록
    .delete() 호출 시 deleted_at = 현재 시각으로 기록
    db에서 완전 삭제하려면 .hard_delete()
    SoftDeleteManager → 기본적으로 deleted_at=None인 데이터만 조회
    """

    deleted_at = models.DateTimeField(blank=True, null=True)

    # ✅ soft delete 기본 매니저 (삭제 안 된 데이터만 조회)
    objects = SoftDeleteManager()

    # ✅ 전체 매니저 (삭제된 데이터 포함)
    all_objects = models.Manager()

    class Meta:
        abstract = True  # 실제 테이블로 생성되지 않음
        ordering = ["-id"]  # 기본 정렬: 최신순

    def delete(self, using=None, keep_parents=False):
        """실제 삭제 대신 deleted_at 필드에 현재 시간 기록"""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """DB에서 진짜로 삭제"""
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def is_deleted(self):
        """객체가 삭제 상태인지 여부 반환"""
        return self.deleted_at is not None
