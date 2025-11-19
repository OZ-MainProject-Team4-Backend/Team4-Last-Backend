from rest_framework import serializers

from apps.chat.models import AiChatLogs


class ChatSendSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True)
    detail = serializers.CharField(required=False, allow_blank=True)
    weather = serializers.JSONField(required=False)
    profile = serializers.JSONField(required=False)
    session_id = serializers.IntegerField(required=False, allow_null=True)

    lat = serializers.FloatField(required=False)
    lon = serializers.FloatField(required=False)
    city = serializers.CharField(required=False, allow_blank=True)
    district = serializers.CharField(required=False, allow_blank=True)


class AiChatLogReadSerializer(serializers.ModelSerializer):  # ← ModelSerializer 로!
    class Meta:
        model = AiChatLogs
        fields = [
            "id",
            "user",
            "session",
            "model_name",
            "user_question",
            "ai_answer",
            "context",
            "created_at",
        ]
