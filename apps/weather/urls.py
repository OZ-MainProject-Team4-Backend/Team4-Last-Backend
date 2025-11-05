from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.weather.views import WeatherViewSet

router = DefaultRouter()
router.register(r"", WeatherViewSet, basename="weather")

urlpatterns = router.urls
