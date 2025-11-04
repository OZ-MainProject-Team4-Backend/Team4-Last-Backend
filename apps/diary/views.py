from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.diary.models import Diary
from apps.diary.serializers import (
    DiaryCreateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
)


class DiaryViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Diary.objects.filter(user=self.request.user, deleted_at__isnull=True)

    @extend_schema(
        summary="내 일기 목록 조회",
        parameters=[
            OpenApiParameter(
                name="year", description="조회할 연도", required=False, type=int
            ),
            OpenApiParameter(
                name="month", description="조회할 월", required=False, type=int
            ),
        ],
        responses={200: DiaryListSerializer(many=True)},
    )
    def list(self, request):
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        diary_qs = self.get_queryset()

        if year and month:
            diary_qs = diary_qs.filter(date__year=year, date__month=month)

        if not diary_qs.exists():
            return Response(
                {"error": "존재하지 않습니다", "error_status": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DiaryListSerializer(diary_qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            diary = self.get_queryset().get(pk=pk)
        except Diary.DoesNotExist:
            return Response(
                {"error": "존재하지 않습니다", "error_status": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DiaryDetailSerializer(diary)
        return Response(serializer.data)

    def create(self, request):
        serializer = DiaryCreateSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            diary = serializer.save()
            return Response(
                {"diary_id": diary.id, "message": "일기 작성 완료"},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "error": "작성 실패",
                "detail": serializer.errors,
                "error_status": "diary_create_failed",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, pk=None):
        diary = get_object_or_404(self.get_queryset(), pk=pk)
        partial = request.method == "PATCH"
        serializer = DiaryCreateSerializer(
            diary, data=request.data, partial=partial, context={"request": request}
        )
        if serializer.is_valid():
            diary = serializer.save()
            return Response(DiaryDetailSerializer(diary).data)
        return Response(
            {
                "error": "수정 실패",
                "detail": serializer.errors,
                "error_status": "update_failed",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, pk=None):
        diary = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            diary.deleted_at = timezone.now()
            diary.save()
            return Response({"message": "삭제 완료"}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "삭제 실패", "error_status": "delete_failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
