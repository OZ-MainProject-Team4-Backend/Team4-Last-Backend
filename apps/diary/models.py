from django.db import models

from apps.core.models import SoftDeleteModel
from apps.users.models import User
from apps.weather.models import WeatherData


class Diary(SoftDeleteModel):

    EMOTION_CHOICES = [
        (0, "😊 기쁨"),
        (1, "😲 놀람"),
        (2, "😢 슬픔"),
        (3, "😡 화남"),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    date = models.DateField(verbose_name="작성 날짜")
    weather_data = models.ForeignKey(
        WeatherData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    emotion = models.IntegerField(
        choices=EMOTION_CHOICES,
        default=0,
        help_text="오늘의 감정 (0: 기쁨, 1: 놀람, 2: 슬픔, 3: 화남)",
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    image_url = models.URLField(
        max_length=500, blank=True, null=True
    )  # 이미지 없이 저장해도 가능 - 에러발생 X
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date", "-updated_at"]
        db_table = 'diary'
        verbose_name = 'Diary'
        verbose_name_plural = 'Diaries'

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - {self.date} - {self.title}"
