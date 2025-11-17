import logging
import uuid

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.chat.models import AiChatLogs
from apps.chat.serializers import AiChatLogReadSerializer, ChatSendSerializer
from apps.chat.services.chat import chat_and_log

logger = logging.getLogger(__name__)


class AiChatViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["POST"], url_path="send")
    def send(self, request):
        ser = ChatSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        weather = ser.validated_data.get("weather")
        profile = ser.validated_data.get("profile")
        today = timezone.localdate()

        session_id = ser.validated_data.get("session_id")

        if user and not session_id:
            existing_sid = (
                AiChatLogs.objects.filter(user=user, created_at__date=today)
                .order_by("-created_at")
                .values_list("session_id", flat=True)
                .first()
            )
            if existing_sid:
                session_id = str(existing_sid)

        if not session_id:
            session_id = str(uuid.uuid4())

        text = ser.validated_data.get("detail") or ser.validated_data.get("message")

        try:
            result = chat_and_log(
                user=user,
                session_id=session_id,
                user_message=text,
                weather=weather,
                profile=profile,
                model_name="gpt-4o",
            )
            return Response(
                {
                    "response": result["answer"],
                    "session_id": str(session_id),
                    "created_at": timezone.localtime(result["created_at"]).isoformat(),
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("chat send failed")
            return Response(
                {"error": "AI 대화 실패", "error_status": "chat_failed"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    @action(detail=False, methods=["GET"], url_path="session")
    def session(self, request):
        sid_param = request.query_params.get("session_id")
        limit = int(request.query_params.get("limit") or 20)
        before_id = request.query_params.get("before_id")
        today = timezone.localdate()

        user = request.user if request.user.is_authenticated else None

        if sid_param:
            session_id = sid_param
        else:
            if not user:
                return Response(
                    {"error": "세션 없음", "error_status": "session_empty"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            last_sid = (
                AiChatLogs.objects.filter(user=user, created_at__date=today)
                .order_by("-created_at")
                .values_list("session_id", flat=True)
                .first()
            )
            if not last_sid:
                return Response(
                    {"error": "세션 없음", "error_status": "session_empty"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            session_id = str(last_sid)

        qs = AiChatLogs.objects.filter(
            session_id=session_id,
            created_at__date=today,
        )

        if before_id:
            qs = qs.filter(id__lt=before_id)

        qs = qs.order_by("-created_at")[:limit]

        logs = list(qs.values("id", "user_question", "ai_answer", "created_at"))
        logs.reverse()

        if not logs:
            return Response(
                {"error": "세션 없음", "error_status": "session_empty"},
                status=status.HTTP_404_NOT_FOUND,
            )

        out = []
        for row in logs:
            msg_id = row["id"]
            created_at = timezone.localtime(row["created_at"]).isoformat()

            out.append(
                {
                    "id": msg_id,
                    "role": "user",
                    "text": row["user_question"],
                    "created_at": created_at,
                }
            )
            out.append(
                {
                    "id": msg_id,
                    "role": "ai",
                    "text": row["ai_answer"],
                    "created_at": created_at,
                }
            )

        oldest_id = logs[0]["id"]
        has_more = AiChatLogs.objects.filter(
            session_id=session_id,
            created_at__date=today,
            id__lt=oldest_id,
        ).exists()

        return Response(
            {
                "session_id": session_id,
                "created_at": timezone.localtime(logs[0]["created_at"]).isoformat(),
                "messages": out,
                "next_before_id": oldest_id if has_more else None,
                "has_more": has_more,
            },
            status=status.HTTP_200_OK,
        )


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

        today = timezone.localdate()
        qs = qs.filter(created_at__date=today)

        return qs
