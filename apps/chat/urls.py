from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.chat.views import AiChatViewSet, ChatLogViewSet

router = DefaultRouter()

router.register(r"", AiChatViewSet, basename="chat")
router.register(r"logs", ChatLogViewSet, basename="chat_logs")

urlpatterns = [
    path("", include(router.urls)),
]
