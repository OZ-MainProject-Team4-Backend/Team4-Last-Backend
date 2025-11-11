import uuid

from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.chat.models import AiChatLogs
from apps.chat.serializers import AiChatLogReadSerializer, ChatSendSerializer
from apps.chat.services.chat import chat_and_log


class AiChatViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["POST"], url_path="send")
    def send(self, request):
        ser = ChatSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        session_id = ser.validated_data.get("session_id") or uuid.uuid4()
        user = request.user if request.user.is_authenticated else None
        weather = ser.validated_data.get("weather")
        profile = ser.validated_data.get("profile")

        try:
            result = chat_and_log(
                user=user,
                session_id=session_id,
                user_message=ser.validated_data["message"],
                weather=weather,
                profile=profile,
                model_name="gpt-4o",
            )
            return Response(
                {"response": result["answer"], "session_id": str(session_id)},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"error": "AI 대화 실패", "error_status": "chat_failed"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    @action(detail=False, methods=["GET"], url_path="session")
    def session(self, request):
        sid = request.query_params.get("session_id")
        limit = int(request.query_params.get("limit") or 20)

        if not sid and not request.user.is_authenticated:
            return Response(
                {"error": "세션 없음", "error_status": "session_empty"},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = AiChatLogs.objects.all()
        if sid:
            qs = qs.filter(session_id=sid)
        else:
            last_sid = (
                AiChatLogs.objects.filter(user=request.user)
                .order_by("-created_at")
                .values_list("session_id", flat=True)
                .first()
            )
            if not last_sid:
                return Response(
                    {"error": "세션 없음", "error_status": "session_empty"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            qs = qs.filter(session_id=last_sid)

        logs = list(qs.order_by("created_at").values_list("user_question", "ai_answer"))
        if not logs:
            return Response(
                {"error": "세션 없음", "error_status": "session_empty"},
                status=status.HTTP_404_NOT_FOUND,
            )

        out = []
        for uq, aa in logs[-limit:]:
            out.append({"role": "user", "text": uq})
            out.append({"role": "ai", "text": aa})

        return Response(out, status=status.HTTP_200_OK)


class ChatLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AiChatLogReadSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = AiChatLogs.objects.all().order_by("-created_at")
        sid = self.request.query_params.get("session_id")
        if sid:
            qs = qs.filter(session_id=sid)
        user = self.request.user if self.request.user.is_authenticated else None
        if user:
            qs = qs.filter(user=user)
        return qs
