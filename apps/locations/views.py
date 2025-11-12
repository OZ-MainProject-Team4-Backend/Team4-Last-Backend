from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FavoriteLocation
from .serializers import (
    FavoriteLocationSerializer,
    FavoriteLocationAliasSerializer,
)

class FavoriteLocationViewSet(viewsets.ModelViewSet):
    """
    즐겨찾기 지역 CRUD Viewset
    기본 목록 생성, 조회, 수정, 삭제 제공
    SoftDeleteModel 기반 - deleted_at IS NULL 데이터만 조회
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteLocationSerializer

    def get_serializer_class(self):
        """별칭만 수정 가능한 시리얼라이저 사용"""
        if self.action == "partial_update":
            return FavoriteLocationAliasSerializer
        return FavoriteLocationSerializer

    def get_queryset(self):
        """사용자의 즐겨찾기 목록만 조회 (소프트삭제 제외)"""
        return FavoriteLocation.objects.filter(
            user=self.request.user, deleted_at__isnull=True
        ).order_by("order")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        POST /api/locations/favorites/
        즐겨찾기 추가 (serializer.create 로직 호출 후 message 포함 응답)
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()
        except ValidationError as e:
            # ValidationError의 error 코드에 따라 상태 코드 분기
            error = e.detail.get("error") if isinstance(e.detail, dict) else None
            if error == "already_exists":
                return Response(e.detail, status=status.HTTP_409_CONFLICT)
            elif error == "limit_exceeded":
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "즐겨찾기에 추가되었습니다.",
                "id": instance.id,
            },
            status=status.HTTP_201_CREATED,
        )

    # PUT 전체 수정 비활성화
    @extend_schema(exclude=True)
    def update(self, request, *args, **kwargs):
        """
        PUT 요청 비활성화 — 전체 수정은 허용하지 않음
        """
        return Response(
            {
                "error": "method_not_allowed",
                "message": "전체 수정(PUT)은 지원하지 않습니다. PATCH를 사용하세요.",
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/locations/favorites/{id}
        """
        instance = self.get_object()
        instance.delete()

        favorites = FavoriteLocation.objects.filter(
            user=request.user, deleted_at__isnull=True
        ).order_by("order")

        for index, favorite in enumerate(
            favorites
        ):  # 중간에 구멍이 생겼을시 index(0,1,2) 기반으로 order 값 재할당
            if favorite.order != index:
                favorite.order = index
                favorite.save(update_fields=["order"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/locations/favorites/{id}
        별칭 변경
        """
        instance = self.get_object()

        if "order" in request.data:
            return Response(
                {
                    "error": "order_not_allowed_here",
                    "message": "order 변경은 /reorder 엔드포인트를 사용해야 합니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "즐겨찾기 정보가 수정되었습니다."}, status=200)

    @action(detail=False, methods=["patch"], url_path="reorder")
    @transaction.atomic
    def reorder(self, request):
        """
        PATCH /api/locations/favorites/reorder
        """
        user = request.user
        data = request.data

        if not isinstance(data, list):
            return Response(
                {
                    "error": "invalid_format",
                    "message": "리스트 형태로 전달해야 합니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. 사용자 소유의 즐겨찾기 id 목록 받기
        current_ids = set(
            FavoriteLocation.objects.filter(
                user=request.user, deleted_at__isnull=True
            ).values_list("id", flat=True)
        )
        # 2. 사용자 ID 검증
        requested_ids = {item.get("id") for item in request.data}

        if current_ids != requested_ids:
            return Response(
                {
                    "error": "invalid_favorite_id",
                    "message": "잘못된 즐겨찾기 ID가 포함되어 있습니다.",
                },
                status=400,
            )

        # 3. order 중복/누락 검증
        requested_orders = {item.get("order") for item in request.data}
        expected_orders = set(range(len(current_ids)))

        if requested_orders != expected_orders:
            return Response(
                {
                    "error": "invalid_order_values",
                    "message": "order 값은 중복, 누락 없이 연속된 값이어야 합니다.",
                },
                status=400,
            )

        # 4. 업데이트
        for item in request.data:
            FavoriteLocation.objects.filter(
                id=item.get("id"), user=request.user
            ).update(order=item.get("order"))
        return Response({"message": "즐겨찾기 순서가 변경되었습니다."}, status=200)
