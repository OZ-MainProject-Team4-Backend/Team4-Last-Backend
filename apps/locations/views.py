from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FavoriteLocation
from .serializers import (
    FavoriteLocationSerializer,
)


class FavoriteLocationViewSet(viewsets.ModelViewSet):
    """
    즐겨찾기 지역 CRUD Viewset
    기본 목록 생성, 조회, 수정, 삭제 제공
    SoftDeleteModel 기반 - deleted_at IS NULL 데이터만 조회
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteLocationSerializer

    def get_queryset(self):
        """사용자의 즐겨찾기 목록만 조회 (소프트삭제 제외)"""
        return FavoriteLocation.objects.filter(
            user=self.request.user, deleted_at__isnull=True
        ).order_by("order")

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
                {"detail": "order 변경은 /reorder 엔드포인트를 사용해야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=["patch"], url_path="reorder")
    def reorder(self, request):
        """
        PATCH /api/locations/favorites/reorder
        이 로직은 다음 pr에서 구현 예정
        """
        pass
