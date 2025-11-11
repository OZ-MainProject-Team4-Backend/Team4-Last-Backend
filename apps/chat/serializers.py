from rest_framework import serializers

from apps.chat.models import AiChatLogs


class ChatSendSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False)
    message = serializers.CharField(max_length=500)
    weather = serializers.JSONField(required=False)
    profile = serializers.JSONField(required=False)


class AiChatLogReadSerializer(serializers.ModelSerializer):  # ← ModelSerializer 로!
    class Meta:
        model = AiChatLogs
        fields = [
            "id",
            "session_id",
            "model_name",
            "user_question",
            "ai_answer",
            "context",
            "created_at",
        ]
