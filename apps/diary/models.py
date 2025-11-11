from django.db import models
from apps.users.models import User
from apps.weather.models import WeatherData


class Diary(models.Model):

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="작성 날짜")
    weather_data = models.ForeignKey(
        WeatherData, on_delete=models.SET_NULL, null=True, blank=True
    )
    emotion = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    notes = models.TextField()
    image = models.ImageField(
        upload_to='diary_images/%Y/%m/%d/',  # 파일이 저장될 경로 (날짜별로 분리)
        blank=True,
        null=True,
        verbose_name="첨부 이미지 파일",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date", "-updated_at"]
        db_table = 'diary'
        verbose_name = 'Diary'
        verbose_name_plural = 'Diaries'

    def __str__(self):
        return f"{self.date} - {self.title}"


#
