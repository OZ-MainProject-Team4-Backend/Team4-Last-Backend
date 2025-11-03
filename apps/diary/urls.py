from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DiaryViewSet

app_name = "diary"

router = DefaultRouter()
router.register(r"", DiaryViewSet, basename="diary")

urlpatterns = [
    path("", include(router.urls)),
]
