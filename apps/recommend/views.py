from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CoordsRecommendSerializer,
    LocationRecommendSerializer,
    OutfitRecommendSerializer,
)
from .services.recommend_service import create_by_coords, create_by_location


class OutfitRecommendByCoordsView(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(
        summary="좌표 기반 복장 추천",
        request={"application/json": CoordsRecommendSerializer},
        responses={200: OutfitRecommendSerializer},
        tags=["Recommend"],
    )
    def post(self, request):
        ser = CoordsRecommendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        lat = ser.validated_data["latitude"]
        lon = ser.validated_data["longitude"]

        result = create_by_coords(request.user, lat, lon)
        return Response(OutfitRecommendSerializer(result).data)


class OutfitRecommendByLocationView(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(
        summary="지역 기반 복장 추천",
        request={"application/json": LocationRecommendSerializer},
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
