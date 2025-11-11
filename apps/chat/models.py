import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.manager import Manager as DjangoManager

WEATHER_CHOICES = [
    ("", "ANY"),
    ("Clear", "Clear"),
    ("Clouds", "Clouds"),
    ("Rain", "Rain"),
    ("Snow", "Snow"),
    ("Drizzle", "Drizzle"),
    ("Thunderstorm", "Thunderstorm"),
    ("Mist", "Mist"),
    ("Fog", "Fog"),
    ("Haze", "Haze"),
    ("Smoke", "Smoke"),
    ("Dust", "Dust"),
    ("Squall", "Squall"),
    ("Tornado", "Tornado"),
]


class AiModelSettings(models.Model):
    name = models.CharField(max_length=150, unique=True)
    temperature_min = models.FloatField()
    temperature_max = models.FloatField()
    humidity_min = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    humidity_max = models.IntegerField(
        default=100, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    weather_condition = models.CharField(
        max_length=100, blank=True, choices=WEATHER_CHOICES
    )
    category_combo = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: DjangoManager["AiModelSettings"] = models.Manager()

    class Meta:
        db_table = "ai_model_settings"
        indexes = [
            models.Index(fields=["active"]),
            models.Index(fields=["weather_condition"]),
            models.Index(fields=["temperature_min", "temperature_max"]),
            models.Index(fields=["humidity_min", "humidity_max"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(temperature_min__lte=models.F("temperature_max")),
                name="chk_temp_min_le_max",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(humidity_min__gte=0)
                    & models.Q(humidity_min__lte=100)
                    & models.Q(humidity_max__gte=0)
                    & models.Q(humidity_max__lte=100)
                    & models.Q(humidity_min__lte=models.F("humidity_max"))
                ),
                name="chk_humidity_range_0_100",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.temperature_min} ~ {self.temperature_max}°C, {self.humidity_min} ~ {self.humidity_max}%, {self.weather_condition or 'ANY'})"


class AiChatLogs(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chat_logs",
        null=True,
        blank=True,
    )
    model_setting = models.ForeignKey(
        AiModelSettings,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logs",
    )
    session_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    model_name = models.CharField(max_length=100, blank=True)
    user_question = models.TextField()
    ai_answer = models.TextField()
    context = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    objects: DjangoManager["AiChatLogs"] = models.Manager()
    id: int

    class Meta:
        db_table = "ai_chat_logs"
        indexes = [models.Index(fields=["user", "session_id", "-created_at"])]

    def __str__(self):
        return f"{self.user_id}/{self.session_id} - {self.created_at:%Y-%m-%d %H:%M:%S}"
