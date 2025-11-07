from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Diary
from .serializers import (
    DiaryCreateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
    DiaryUpdateSerializer,
)


class DiaryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Diary.objects.filter(deleted_at__isnull=True)

    #  액션별 serializer 분기
    def get_serializer_class(self):
        if self.action == "list":
            return DiaryListSerializer
        elif self.action == "retrieve":
            return DiaryDetailSerializer
        elif self.action == "create":
            return DiaryCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return DiaryUpdateSerializer
        return DiaryDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Diary.objects.filter(user=user, deleted_at__isnull=True)
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")

        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)

        return queryset

    #  생성 시 user 자동 세팅
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    #  soft delete
    def perform_destroy(self, instance):
        instance.delete()

    #  일기생성
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                {"diary_id": serializer.instance.id, "message": "일기 작성 완료"},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError:
            return Response({"error": "작성 실패"}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"message": "일기 수정 완료"})
        except ValidationError:
            return Response({"error": "수정 실패"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError:
            return Response({"error": "삭제 실패"}, status=status.HTTP_400_BAD_REQUEST)
