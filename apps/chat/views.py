import logging
import uuid
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.chat.models import AiChatLogs, ChatSession
from apps.chat.serializers import AiChatLogReadSerializer, ChatSendSerializer
from apps.chat.services.chat import chat_and_log
from apps.chat.services.weather_for_chat import get_weather_for_chat

logger = logging.getLogger(__name__)


class AiChatViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=ChatSendSerializer,
        responses={200: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                '기본 요청 예시',
                value={"message": "오늘 뭐 입지?"},
                request_only=True,
            )
        ],
    )
    @action(detail=False, methods=["POST"], url_path="send")
    def send(self, request):
        ser = ChatSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        weather = ser.validated_data.get("weather")
        profile = ser.validated_data.get("profile")
        text = (
            ser.validated_data.get("detail") or ser.validated_data.get("message") or ""
        )

        lat = ser.validated_data.get("lat")
        lon = ser.validated_data.get("lon")
        city = ser.validated_data.get("city")
        district = ser.validated_data.get("district")

        SESSION_TTL_MINUTES = 10

        session_id = ser.validated_data.get("session_id")
        chat_session = None

        if not weather:
            try:
                weather = get_weather_for_chat(
                    user=user,
                    lat=lat,
                    lon=lon,
                    city=city,
                    district=district,
                )
            except Exception:
                logger.exception("get_weather_for_chat failed")
                weather = None

        if session_id is not None:
            chat_session = ChatSession.objects.filter(id=session_id).first()
            if chat_session is None:
                return Response(
                    {
                        "error": "세션을 찾을 수 없습니다.",
                        "error_status": "session_not_found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        if chat_session is None and user is not None:
            last_session = (
                ChatSession.objects.filter(user=user).order_by("-created_at").first()
            )

            if last_session:
                last_log = (
                    AiChatLogs.objects.filter(session=last_session)
                    .order_by("-created_at")
                    .first()
                )

                if last_log and last_log.created_at >= timezone.now() - timedelta(
                    minutes=SESSION_TTL_MINUTES
                ):
                    chat_session = last_session

        if chat_session is None:
            chat_session = ChatSession.objects.create(user=user)

        try:
            result = chat_and_log(
                user=user,
                session=chat_session,
                user_message=text,
                weather=weather,
                profile=profile,
                model_name="gpt-4o",
            )
            return Response(
                {
                    "response": result["answer"],
                    "session_id": chat_session.id,
                    "created_at": timezone.localtime(result["created_at"]).isoformat(),
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("chat send faild")
            return Response(
                {"error": "AI 대화 실패", "error_status": "chat_failed"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="session_id",
                type=OpenApiTypes.INT,
                required=True,
                location=OpenApiParameter.QUERY,
                description="조회할 세션 ID",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                required=False,
                location=OpenApiParameter.QUERY,
                description="가져올 로그 개수 (기본 20)",
            ),
            OpenApiParameter(
                name="before_id",
                type=OpenApiTypes.INT,
                required=False,
                location=OpenApiParameter.QUERY,
                description="이 ID 보다 작은 로그만 조회 (무한스크롤)",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["GET"], url_path="session")
    def session(self, request):
        sid_param = request.query_params.get("session_id")
        limit = int(request.query_params.get("limit") or 20)
        before_id = request.query_params.get("before_id")
        today = timezone.localdate()

        if not sid_param:
            return Response(
                {
                    "error": "session_id 파라미터가 필요합니다.",
                    "error_status": "session_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session_id = int(sid_param)
        except ValueError:
            return Response(
                {
                    "error": "session_id 는 숫자여야 합니다.",
                    "error_status": "invalid_session_id",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ChatSession.objects.filter(id=session_id).exists():
            return Response(
                {"error": "세션 없음", "error_status": "session_empty"},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = AiChatLogs.objects.filter(
            session_id=session_id,
            created_at__date=today,
        )

        if before_id:
            try:
                before_id_int = int(before_id)
                qs = qs.filter(id__lt=before_id_int)
            except ValueError:
                pass

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
