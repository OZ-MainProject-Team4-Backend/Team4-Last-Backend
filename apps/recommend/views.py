from drf_spectacular.utils import extend_schema
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CoordsRecommendSerializer,
    LocationRecommendSerializer,
    OutfitRecommendSerializer,
)
from .services.recommend_service import create_by_coords, create_by_location


class OutfitRecommendView(APIView):

    @extend_schema(
        summary="복장 추천",
        description=(
            "latitude/longitude 또는 city/district 중 하나만 전달하면 추천 결과를 반환합니다."
        ),
        responses={200: OutfitRecommendSerializer},
        tags=["Recommend"],
    )
    def get(self, request):
        lat = request.query_params.get("latitude")
        lon = request.query_params.get("longitude")
        city = request.query_params.get("city")
        district = request.query_params.get("district")

        if lat and lon:
            result = create_by_coords(request.user, float(lat), float(lon))
            return Response(OutfitRecommendSerializer(result).data)

        if city and district:
            result = create_by_location(request.user, city, district)
            return Response(OutfitRecommendSerializer(result).data)

        raise ValidationError(
            "latitude+longitude 또는 city+district 중 하나를 제공해야 합니다."
        )
