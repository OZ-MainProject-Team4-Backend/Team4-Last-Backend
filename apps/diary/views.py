from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from .models import Diary
from .serializers import (
    DiaryCreateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
    DiaryUpdateSerializer,
)
from apps.weather.models import WeatherData, WeatherLocation
from apps.weather import repository as weather_repo
from apps.weather.services import openweather as ow

class DiaryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Diary.objects.filter(deleted_at__isnull=True)

    #  액션별 serializer 분기
    def get_serializer_class(self):
        if self.action == "list":
            return DiaryListSerializer
        elif self.action == "retrieve":
            return DiaryDetailSerializer
        elif self.action == "create":
            return DiaryCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return DiaryUpdateSerializer
        return DiaryDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Diary.objects.filter(user=user, deleted_at__isnull=True)
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")

        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)

        return queryset


    def perform_create(self, serializer):
        user = self.request.user
        lat = serializer.validated_data.get("lat")
        lon = serializer.validated_data.get("lon")

        #  1. 날씨 데이터 조회
        try:
            current_weather = ow.get_current(lat=lat, lon=lon)
        except ow.ProviderTimeout:
            raise ValidationError({"detail": "weather_provider_timeout"})
        except ow.ProviderError as e:
            raise ValidationError({"detail": str(e) or "weather_provider_error"})

        #  2. WeatherLocation 생성 or 갱신
        city = (current_weather.get("raw") or {}).get("name") or ""
        location, _ = WeatherLocation.objects.get_or_create(
            lat=lat,
            lon=lon,
            defaults={"city": city, "district": "", "dp_name": city or f"{lat},{lon}"},
        )

        #  3. WeatherData 저장 (repository 사용)
        weather_data = weather_repo.save_current(
            location=location, current=current_weather
        )

        #  4. Diary 저장 (날씨 자동 연결)
        serializer.save(user=user, weather_data=weather_data)

    #  soft delete
    def perform_destroy(self, instance):
        instance.delete()

    #  일기생성
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"diary_id": serializer.instance.id, "message": "일기 작성 완료"},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "일기 수정 완료"})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError:
            return Response({"error": "삭제 실패"}, status=status.HTTP_400_BAD_REQUEST)
