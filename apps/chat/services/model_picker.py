from typing import Optional

from django.db.models import F, Q

from apps.chat.models import AiModelSettings


def pick_model_setting(
    temp_c: float, humidity: int | None, condition: str | None
) -> Optional[AiModelSettings]:
    qs = AiModelSettings.objects.filter(
        active=True,
        temperature_min__lte=temp_c,
        temperature_max__gte=temp_c,
    )
    if humidity is not None:
        qs = qs.filter(humidity_min__lte=humidity, humidity_max__gte=humidity)
    if condition:
        qs = qs.filter(Q(weather_condition="") | Q(weather_condition=condition))
    else:
        qs = qs.filter(Q(weather_condition=""))

    qs = qs.annotate(
        temp_span=F("temperature_max") - F("temperature_min"),
        humidity_span=F("humidity_max") - F("humidity_min"),
    ).order_by("temperature_span", "humidity_span", "id")

    return qs.first()
