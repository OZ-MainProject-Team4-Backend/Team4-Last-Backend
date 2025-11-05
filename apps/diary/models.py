from django.db import models

from apps.core.models import SoftDeleteModel
from apps.users.models import User
from apps.weather.models import WeatherData


class Diary(SoftDeleteModel):

    SATISFACTION_CHOICES = [
        (0, "😔 별로예요"),
        (1, "😐 보통이에요"),
        (2, "🙂 좋아요"),
        (3, "😄 아주 좋아요"),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="diaries",
        verbose_name="작성자",
    )
    date = models.DateField(verbose_name="작성 날짜")
    weather_data = models.ForeignKey(
        WeatherData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diaries",
    )
    satisfaction = models.IntegerField(
        choices=SATISFACTION_CHOICES,
        default=1,
        help_text="오늘의 기분 점수 (0~3)",  # default 값 = 1
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    image_url = models.URLField(
        max_length=255, blank=True, null=True
    )  # 이미지 없이 저장해도 가능 - 에러발생 X
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'diary'
        verbose_name = 'Diary'
        verbose_name_plural = 'Diaries'

    def __str__(self):
        return f"{self.date} - {self.title}"
