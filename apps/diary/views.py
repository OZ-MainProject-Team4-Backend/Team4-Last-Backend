import os
import re
import uuid
from datetime import datetime, timedelta

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.weather import repository as weather_repo
from apps.weather.models import WeatherLocation
from apps.weather.services import openweather as ow

from .models import Diary
from .serializers import (
    DiaryCreateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
    DiaryUpdateSerializer,
)

# 파일 업로드 방어 함수
# ==========================
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def safe_upload(file_obj, user_id):
    if not file_obj or not getattr(file_obj, "name", ""):
        raise ValidationError("업로드된 파일이 없습니다.")

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"허용되지 않은 파일 확장자: {ext}")
    if file_obj.size > MAX_FILE_SIZE:
        raise ValidationError(f"파일 크기 제한 초과: {file_obj.size} bytes")

    filename = f"{uuid.uuid4().hex}{ext}"
    key = f"diary/{user_id}/{filename}"
    key = re.sub(r"[^A-Za-z0-9_\-./]", "_", key)
    key = re.sub(r"/+", "/", key)

    if getattr(file_obj, "content_type", None):
        file_obj = ContentFile(file_obj.read(), name=filename)

    try:
        bucket = default_storage.bucket
        extra_args = {}
        if getattr(file_obj, "content_type", None):
            extra_args["ContentType"] = file_obj.content_type

        bucket.Object(key).put(Body=file_obj, **extra_args)

    except Exception as e:
        raise ValidationError(f"S3 업로드 실패: {str(e)}")

    return key


class DiaryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  #  multipart/form-data 지원
    queryset = Diary.objects.all()

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
        queryset = Diary.objects.filter(user=user)
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")

        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)

        return queryset

    def handle_file_upload(self, file_obj):
        import uuid

        from django.core.files.storage import default_storage

        key = f"diary/{self.request.user.id}/{uuid.uuid4().hex}.{file_obj.name.split('.')[-1]}"

        # S3 업로드 시 ACL 추가
        saved_path = default_storage.save(
            key,
            file_obj,
            extra_args={"ACL": "public-read"},  # ← 여기서 권한 설정
        )
        return saved_path

    @transaction.atomic  # 날씨 저장 중 오류 발생 시 일기까지 저장되지 않도록 롤백
    def perform_create(self, serializer):

        # 1. 파일 업로드 처리
        file_obj = serializer.validated_data.pop("image", None)
        if file_obj:
            serializer.validated_data["image"] = self.handle_file_upload(file_obj)

        # 2. 날씨 처리
        lat = serializer.validated_data.pop("lat", None)
        lon = serializer.validated_data.pop("lon", None)
        date = serializer.validated_data.get("date")
        today = datetime.now().date()
        current_weather = None  # 초기값 설정

        #  1. 날씨 데이터 조회
        try:
            if lat is not None and lon is not None:
                if date == today:
                    current_weather = ow.get_current(lat=lat, lon=lon)
                elif today - timedelta(days=5) <= date < today:
                    dt = datetime.combine(date, datetime.min.time())
                    current_weather = ow.get_historical(lat=lat, lon=lon, date=dt)
                else:
                    current_weather = None
            else:
                current_weather = None
        except ow.ProviderTimeout:
            raise ValidationError({"detail": "weather_provider_timeout"})
        except ow.ProviderError as e:
            raise ValidationError({"detail": str(e) or "weather_provider_error"})
        except Exception:
            current_weather = None  # 날씨 조회 실패시, 일기는 저장

        #  2. WeatherLocation 생성 or 갱신
        city = (
            current_weather.get("raw", {}).get("name")
            if isinstance(current_weather, dict)
            else ""
        ) or ""
        district = ""

        location, _ = WeatherLocation.objects.get_or_create(
            city=city,
            district=district,
            defaults={
                "lat": lat,
                "lon": lon,
                "dp_name": city or f"{lat},{lon}",
            },
        )

        #  3. WeatherData 저장 (repository 사용)
        weather_data = None
        if current_weather and isinstance(current_weather, dict):
            weather_data = weather_repo.save_current(
                location=location, current=current_weather
            )

        #  4. Diary 저장 (날씨 자동 연결)
        serializer.save(user=self.request.user, weather_data=weather_data)

    @transaction.atomic
    def perform_update(self, serializer):
        file_obj = serializer.validated_data.pop("image", None)
        if file_obj:
            if serializer.instance.image:
                try:
                    default_storage.delete(serializer.instance.image.name)
                except Exception:
                    pass
            serializer.validated_data["image"] = self.handle_file_upload(file_obj)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.image:
            try:
                default_storage.delete(instance.image.name)  # name으로 삭제
            except Exception:
                pass
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
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
