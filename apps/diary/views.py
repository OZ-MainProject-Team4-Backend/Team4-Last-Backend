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
    queryset = Diary.objects.filter(is_deleted=False)

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

    #  본인 일기만
    def get_queryset(self):
        user = self.request.user
        queryset = Diary.objects.filter(user=user, is_deleted=False)
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
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])

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
        except Exception as e:
            # 로그로 기록하거나 디버깅 시 확인 가능
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"message": "일기 수정 완료"})
        except ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "일기가 삭제되었습니다."},
            status=status.HTTP_200_OK,
        )
