from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.chat.views import AiChatViewSet, ChatLogViewSet

router = DefaultRouter()
router.register(r"chat", AiChatViewSet, basename="chat")
router.register(r"chat/logs", ChatLogViewSet, basename="chat-logs")

urlpatterns = [
    path("api/", include(router.urls)),
]
