from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import FavoriteLocation
from .serializers import (
    FavoriteLocationSerializer,
)


class FavoriteLocationViewSet(viewsets.ModelViewSet):
    """
    즐겨찾기 지역 CRUD Viewset
    기본 목록, 생성, 조회, 수정, 삭제 제공
    SoftDeleteModel 기반 - deleted_at IS NULL 데이터만 조회
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteLocationSerializer

    def get_queryset(self):
        """사용자의 즐겨찾기 목록만 조회 (소프트삭제 제외)"""
        return FavoriteLocation.objects.filter(
            user=self.request.user,
            deleted_at__isnull=True
        ).order_by("order")

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/locations/favorites/{id}
        """



    def alias_update(self):
        """
        PATCH /api/locations/favorites/{id}
        """
        pass


    def reorder(self):
        """
        PATCH /api/locations/favorites/reorder
        """
        pass