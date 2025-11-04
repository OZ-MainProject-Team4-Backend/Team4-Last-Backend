from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.weather.models import WeatherData


class SoftDeleteMixin(models.Model): #Soft Delete

    deleted_at = models.DateTimeField(blank=True, null=True)  # 삭제 시각 (Soft Delete)

    class Meta:
        abstract = True  # DB 테이블 생성 안 함

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()  # 실제 삭제 대신 삭제 시각 기록
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None  # 삭제 복구
        self.save(update_fields=["deleted_at"])


class Diary(SoftDeleteMixin, models.Model):

    SATISFACTION_CHOICES = [
        (0, "😔 별로예요"),
        (1, "😐 보통이에요"),
        (2, "🙂 좋아요"),
        (3, "😄 아주 좋아요"),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    weather_data = models.ForeignKey(WeatherData, on_delete=models.SET_NULL, null=True)
    satisfaction = models.IntegerField(
        choices=SATISFACTION_CHOICES,
        help_text="오늘의 기분 점수 (0~3)"
    )
    title = models.CharField(max_length=255)
    notes = models.TextField()
    image_url = models.URLField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'diary'
        verbose_name = 'Diary'
        verbose_name_plural = 'Diaries'

    def __str__(self):
        return f"{self.date} - {self.title}"
