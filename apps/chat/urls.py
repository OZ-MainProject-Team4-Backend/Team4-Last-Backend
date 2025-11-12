from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.chat.views import AiChatViewSet, ChatLogViewSet

# router = DefaultRouter()
# router.register(r"chat", AiChatViewSet, basename="chat")
# router.register(r"chat-logs", ChatLogViewSet, basename="chat-logs")
#
# urlpatterns = [
#     path("", include(router.urls)),
# ]

from django.urls import path
from apps.chat.views import AiChatViewSet, ChatLogViewSet

chat_send = AiChatViewSet.as_view({"post": "send"})
chat_session = AiChatViewSet.as_view({"get": "session"})
chat_logs_list = ChatLogViewSet.as_view({"get": "list"})

urlpatterns = [
    path("chat/send/", chat_send, name="chat-send"),
    path("chat/session/", chat_session, name="chat-session"),
    path("chat/logs/", chat_logs_list, name="chat-logs"),
]
