from django.conf import settings
from django.db import models


class OutfitRecommendation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="outfit_recommendations",
    )
    weather_data = models.ForeignKey(
        "weather.WeatherData",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outfit_recommendations",
    )

    rec_1 = models.TextField()
    rec_2 = models.TextField()
    rec_3 = models.TextField()
    explanation = models.TextField()
    image_url = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "outfit_recommendations"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"OutfitRecommendation(user={self.user_id}, {self.created_at:%Y-%m-%d})"
