from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import OutfitRecommendSerializer
from .services.recommend_service import generate_outfit_recommend


class OutfitRecommendView(generics.GenericAPIView):
    """
    좌표 기반 복장 추천 API
    - 사용자 인증 필요
    - POST 요청 시 위도(latitude), 경도(longitude)를 받아 추천 생성
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OutfitRecommendSerializer

    @extend_schema(
        summary="좌표 기반 복장 추천",
        description="사용자의 위도, 경도를 기반으로 날씨에 맞는 코디 3종을 추천합니다.",
        request={
            "application/json": {
                "latitude": 37.5665,
                "longitude": 126.9780,
            }
        },
        responses={
            201: OutfitRecommendSerializer,
            400: {
                "type": "object",
                "properties": {
                    "error_code": {"type": "string"},
                    "message": {"type": "string"},
                },
                "example": {
                    "error_code": "invalid_params",
                    "message": "위도 또는 경도 누락",
                },
            },
        },
        examples=[
            OpenApiExample(
                "성공 예시",
                summary="정상 응답 예시",
                value={
                    "recommendations": ["니트 + 데님", "후드 + 조거", "셔츠 + 슬랙스"],
                    "explanation": "오늘은 맑고 선선한 날씨라 가벼운 니트를 추천드려요!",
                },
                response_only=True,
            )
        ],
    )
    def post(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        user = request.user

        # 좌표 누락 시 에러 처리
        if not latitude or not longitude:
            return Response(
                {"error_code": "invalid_params", "message": "위도 또는 경도 누락"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 추천 생성
        reco = generate_outfit_recommend(user, latitude, longitude)

        # 직렬화 후 반환함
        serializer = self.get_serializer(reco)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
