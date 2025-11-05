from rest_framework import status, views
from rest_framework.response import Response

from apps.locations.models import FavoriteLocation
from apps.weather.models import WeatherLocation

from .models import OutfitRecommendation
from .serializers import OutfitRecommendSerializer
from .services.recommend_service import generate_outfit_recommend
from .services.weather_service import get_weather_data


class OutfitRecommendByLocationView(views.APIView):
    """
    POST /api/recommend/outfit/location
    사용자 즐겨찾기 지역 기반 복장 추천
    """

    def post(self, request):
        city = request.data.get("city")
        district = request.data.get("district")

        # 입력값 검증
        if not city or not district:
            return Response(
                {"error_code": "invalid_params", "message": "city 또는 district 누락"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 즐겨찾기 위치 확인 (Soft Delete 제외)
        location = FavoriteLocation.objects.filter(
            city=city, district=district, deleted_at__isnull=True
        ).first()
        if not location:
            return Response(
                {
                    "error_code": "favorite_not_found",
                    "message": f"{city} {district} 지역의 즐겨찾기 정보가 없습니다.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # WeatherLocation 테이블에서 해당 지역의 위도/경도 조회
        weather_loc = WeatherLocation.objects.filter(
            city=city, district=district
        ).first()
        if not weather_loc:
            return Response(
                {
                    "error_code": "location_not_found",
                    "message": f"{city} {district} 지역의 좌표 정보를 찾을 수 없습니다.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 실제 위도/경도로 날씨 조회
        weather = get_weather_data(latitude=weather_loc.lat, longitude=weather_loc.lon)

        # 룰 기반 복장 추천 생성
        outfit_data = generate_outfit_recommend(
            request.user, weather_loc.lat, weather_loc.lon
        )

        # 추천 결과 저장
        rec = OutfitRecommendation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            weather_data=None,
            rec_1=outfit_data["rec_1"],
            rec_2=outfit_data["rec_2"],
            rec_3=outfit_data["rec_3"],
            explanation=outfit_data["explanation"],
        )

        # 직렬화 후 반환
        serializer = OutfitRecommendSerializer(rec)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OutfitRecommendByCoordsView(views.APIView):
    """
    POST /api/recommend/outfit/coords
    좌표 기반 복장 추천
    """

    def post(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        # 입력값 검증
        if not latitude or not longitude:
            return Response(
                {
                    "error_code": "invalid_params",
                    "message": "위도 또는 경도가 누락되었습니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 날씨 조회
        weather = get_weather_data(float(latitude), float(longitude))

        # 룰 기반 복장 추천 생성
        outfit_data = generate_outfit_recommend(request.user, latitude, longitude)

        # 추천 결과 저장
        rec = OutfitRecommendation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            weather_data=None,
            rec_1=outfit_data["rec_1"],
            rec_2=outfit_data["rec_2"],
            rec_3=outfit_data["rec_3"],
            explanation=outfit_data["explanation"],
        )

        # 직렬화 후 반환
        serializer = OutfitRecommendSerializer(rec)
        return Response(serializer.data, status=status.HTTP_200_OK)
