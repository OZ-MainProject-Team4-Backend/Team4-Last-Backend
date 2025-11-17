from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CoordsRecommendSerializer,
    LocationRecommendSerializer,
    OutfitRecommendSerializer,
)
from .services.recommend_service import create_by_coords, create_by_location


class OutfitRecommendByCoordsView(APIView):
    @extend_schema(
        summary="좌표 기반 복장 추천",
        request=CoordsRecommendSerializer,
        responses={200: OutfitRecommendSerializer},
        tags=["Recommend"],
    )
    def post(self, request):
        ser = CoordsRecommendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        lat = ser.validated_data["lat"]
        lon = ser.validated_data["lon"]

        result = create_by_coords(request.user, lat, lon)
        return Response(OutfitRecommendSerializer(result).data)


class OutfitRecommendByLocationView(APIView):
    @extend_schema(
        summary="지역 기반 복장 추천",
        request=LocationRecommendSerializer,
        responses={200: OutfitRecommendSerializer},
        tags=["Recommend"],
    )
    def post(self, request):
        ser = LocationRecommendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        city = ser.validated_data["city"]
        district = ser.validated_data["district"]

        result = create_by_location(request.user, city, district)
        return Response(OutfitRecommendSerializer(result).data)
