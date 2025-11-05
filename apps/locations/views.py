from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from .models import FavoriteLocation
from .serializers import FavoriteLocationSerializer


class FavoriteLocationViewSet(viewsets.ModelViewSet):
    """
    즐겨찾기 위치 CRUD Viewset
    기본적으로 SoftDelete된 데이터는 제외하여 조회됨 (SoftDeleteModel.objects 사용)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteLocationSerializer

    def get_queryset(self):
        return FavoriteLocation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["patch"], url_path="set-default/")
    def set_default(self, request, pk=None):
        """
         PATCH /api/locations/favorites/{id}/set-default/
         해당 위치를 사용자의 기본 위치로 설정
        """
        favorite = self.get_object()

        FavoriteLocation.objects.filter(
            user=request.user,
            is_default=True,
            deleted_at__isnull=True,
        ).update(is_default=False)

        favorite.is_default = True
        favorite.save(update_fields=["is_default"])

        return Response({"message": "기본 위치가 변경되었습니다."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Delete - soft delete(deleted_at 값만 업데이트)
        """

        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)