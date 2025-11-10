from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

from apps.diary.serializers import (
    DiaryListSerializer,
    DiaryDetailSerializer,
    DiaryCreateSerializer,
    DiaryUpdateSerializer,
)
from apps.diary.models import Diary
from apps.users.models import User
from apps.weather.models import WeatherData, WeatherLocation
from datetime import date as date_obj


def generate_test_image():
    """테스트용 진짜 이미지 바이트 생성"""
    file = BytesIO()
    image = Image.new("RGB", (10, 10), "blue")  # 파란색 10x10 이미지
    image.save(file, "JPEG")
    file.seek(0)
    return SimpleUploadedFile("test_image.jpg", file.read(), content_type="image/jpeg")


class DiarySerializerTest(TestCase):
    def setUp(self):
        """테스트에 필요한 기본 데이터 생성"""
        # 사용자 생성
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            name="테스트이름",
            nickname="테스트닉",
            gender="F",
            age_group="20s",
        )

        # 날씨 위치 및 데이터 생성
        self.location = WeatherLocation.objects.create(
            city="Seoul",
            district="Jongno",
            lat=37.5665,
            lon=126.9780,
            dp_name="Seoul Jongno",
        )

        self.weather = WeatherData.objects.create(
            location=self.location,
            base_time=timezone.now(),
            valid_time=timezone.now(),
            temperature=20.1,
            feels_like=19.8,
            humidity=60,
            rain_probability=10,
            rain_volume=0.0,
            wind_speed=2.5,
            condition="Cloudy",
            icon="03d",
            raw_payload={},
        )

        # 일기 생성
        self.diary = Diary.objects.create(
            user=self.user,
            date=date_obj(2025, 1, 1),
            title="테스트 일기",
            emotion=0,
            notes="테스트 내용",
            weather_data=self.weather,
        )

        # 테스트용 실제 이미지
        self.test_image = generate_test_image()

    # 목록조회 Serializer 테스트
    def test_list_serializer(self):
        serializer = DiaryListSerializer(instance=self.diary)
        data = serializer.data
        self.assertIn("id", data)
        self.assertIn("title", data)
        self.assertIn("date", data)
        self.assertEqual(data["title"], "테스트 일기")

    # 상세조회 Serializer 테스트
    def test_detail_serializer(self):
        serializer = DiaryDetailSerializer(instance=self.diary)
        data = serializer.data
        self.assertEqual(data["emotion"], 0)
        self.assertEqual(data["weather"]["condition"], "Cloudy")
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    # 생성 Serializer 유효성 검사 테스트
    def test_create_serializer_valid(self):
        """정상 데이터 입력 시 유효성 통과 확인"""
        data = {
            "date": "2025-01-05",
            "title": "새로운 일기",
            "emotion": 2,
            "notes": "테스트 작성",
            "lat": 37.5665,
            "lon": 126.9780,
        }
        serializer = DiaryCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_serializer_missing_lat_lon(self):
        """lat/lon 누락 시 유효성 실패"""
        data = {
            "date": "2025-01-05",
            "title": "위치 누락 테스트",
            "emotion": 1,
            "notes": "위치가 없습니다",
        }
        serializer = DiaryCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("lat", serializer.errors)
        self.assertIn("lon", serializer.errors)

    # 수정 Serializer 테스트
    def test_update_serializer(self):
        """업데이트용 serializer가 필드 검증을 정상 수행하는지 확인"""
        update_data = {
            "title": "수정된 제목",
            "emotion": 3,
            "notes": "내용 변경됨",
            "image": self.test_image,
        }
        serializer = DiaryUpdateSerializer(instance=self.diary, data=update_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_diary = serializer.save()
        self.assertEqual(updated_diary.title, "수정된 제목")
        self.assertEqual(updated_diary.emotion, 3)
        self.assertIsNotNone(updated_diary.image)
