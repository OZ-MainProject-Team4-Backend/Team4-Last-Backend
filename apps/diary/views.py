from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.diary.models import Diary
from apps.diary.serializers import (
    DiaryCreateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
    DiaryUpdateSerializer,
)


class DiaryViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Diary.objects.filter(user=self.request.user, deleted_at__isnull=True)

    # [GET] 내 일기 목록 조회
    @extend_schema(
        summary="내 일기 목록 조회",
        description=(
                "로그인한 사용자의 일기를 연도(year)와 월(month)로 필터링하여 조회합니다."
        ),
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

    # [GET] 내 일기 상세 조회
    @extend_schema(
        summary="일기 상세 조회",
        description="특정 일기의 상세 정보를 조회합니다.",
        responses={
            200: OpenApiResponse(
                response=DiaryDetailSerializer, description="조회 성공"
            ),
            404: OpenApiResponse(
                description="존재하지 않습니다",
                response={"example": {"error": "존재하지 않습니다"}},
            ),
        },
    )
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

    # [POST] 일기 작성
    @extend_schema(
        summary="일기 작성",
        description="새로운 일기를 작성합니다. (날짜, 제목, 만족도, 메모, 이미지, 날씨 정보 등을 포함).",
        request=DiaryCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="일기 작성 완료",
                response={"example": {"diary_id": 14, "message": "일기 작성 완료"}},
            ),
            400: OpenApiResponse(
                description="작성 실패",
                response={"example": {"error": "작성 실패", "error_status": "diary_create_failed"}},
            ),
        },
    )
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

    #  [PATCH/PUT] 일기 수정
    @extend_schema(
        summary="일기 수정",
        description="기존 일기의 내용을 수정합니다. (제목, 만족도, 메모, 이미지 등 일부 필드만 변경 가능)",
        request=DiaryUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description="수정 성공",
                response={"example": {"message": "수정 완료"}},
            ),
            400: OpenApiResponse(
                description="수정 실패",
                response={
                    "example": {"error": "수정 실패", "error_status": "update_failed"}
                },
            ),
        },
    )
    def update(self, request, pk=None):
        diary = get_object_or_404(self.get_queryset(), pk=pk)
        partial = request.method == "PATCH"
        serializer = DiaryUpdateSerializer(
            diary, data=request.data, partial=partial, context={"request": request}
        )
        if serializer.is_valid():
            diary = serializer.save()
            return Response(
                {"message": "수정 완료", "data": DiaryDetailSerializer(diary).data},
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "error": "수정 실패",
                "error_status": "update_failed",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    #  [DELETE] 일기 삭제 (Soft Delete)
    @extend_schema(
        summary="일기 삭제 (Soft Delete)",
        description="특정 일기를 논리적으로 삭제합니다. (deleted_at 필드가 자동으로 설정됩니다)",
        responses={
            204: OpenApiResponse(description="삭제 완료"),
            400: OpenApiResponse(
                description="삭제 실패",
                response={"example": {"error": "삭제 실패", "error_status": "delete_failed"}},
            ),
        },
    )
    def destroy(self, request, pk=None):
        diary = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            diary.delete()  # SoftDeleteModel의 delete() 사용
            return Response(status=status.HTTP_204_NO_CONTENT)
        except IntegrityError:
            return Response(
                {"error": "삭제 실패", "error_status": "delete_failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

