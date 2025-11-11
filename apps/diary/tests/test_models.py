from datetime import date as date_obj
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.diary.models import Diary
from apps.users.models import User
from apps.weather.models import WeatherData, WeatherLocation


class DiaryModelTest(TestCase):
    def setUp(self):
        # User 생성
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            name="테스트 이름",
            nickname="테스트닉",
            gender="women",
            age_group="20",
        )

        # WeatherLocation 생성
        self.location = WeatherLocation.objects.create(
            city="Seoul",
            district="Jongno",
            lat=37.5665,
            lon=126.9780,
            dp_name="Seoul Jongno",
        )

        # WeatherData 생성
        self.weather = WeatherData.objects.create(
            location=self.location,
            base_time=timezone.now(),
            valid_time=timezone.now(),
            temperature=18.5,
            feels_like=17.0,
            humidity=50,
            rain_probability=0,
            rain_volume=0.0,
            wind_speed=3.5,
            condition="Cloudy",
            icon="03d",
            raw_payload={},
        )

        # 테스트용 이미지 파일
        self.test_image_content = b"file_content_here"
        self.test_image = SimpleUploadedFile(
            name="test_image.jpg",
            content=self.test_image_content,
            content_type="image/jpeg",
        )

    def test_create_diary_with_image_and_weather(self):
        """이미지 및 날씨 정보가 포함된 일기 생성 테스트"""
        diary = Diary.objects.create(
            user=self.user,
            date=date_obj(2025, 1, 1),
            title="테스트 일기",
            emotion="sad",
            notes="오늘은 테스트를 했어요.",
            image=SimpleUploadedFile(
                name="test_image.jpg",
                content=self.test_image_content,
                content_type="image/jpeg",
            ),
            weather_data=self.weather,  # None이 아닌 실제 객체 전달
        )
        self.assertEqual(Diary.objects.count(), 1)
        self.assertEqual(diary.user.email, "test@example.com")
        self.assertEqual(diary.weather_data.condition, "Cloudy")
        self.assertIsNotNone(diary.image)

    def test_create_diary_without_weather(self):
        """날씨 정보 없이 일기 생성 테스트"""
        diary = Diary.objects.create(
            user=self.user,
            date=date_obj(2025, 1, 2),
            title="날씨 없는 일기",
            emotion="happy",
            notes="오늘 날씨는 없어요.",
            weather_data=None,  # 반드시 None으로
        )
        self.assertEqual(Diary.objects.count(), 1)
        self.assertIsNone(diary.weather_data)

    def test_str_representation(self):
        """__str__ 메서드 문자열 표현 테스트"""
        diary = Diary.objects.create(
            user=self.user,
            date=date_obj(2025, 1, 3),
            title="문자열 표현 테스트",
            weather_data=None,
            emotion="angry",
            notes="",
        )
        expected_str = f"{diary.date} - {diary.title}"
        self.assertEqual(str(diary), expected_str)

    def test_unique_together_constraint(self):
        """user와 date 조합의 유니크 제약 조건 테스트"""
        Diary.objects.create(
            user=self.user,
            date=date_obj(2025, 1, 4),
            title="첫 번째 일기",
            weather_data=None,
            emotion="excited",
            notes="",
        )
        # 같은 user, 같은 date로 생성 시 예외 발생 확인
        with self.assertRaises(Exception):
            Diary.objects.create(
                user=self.user,
                date=date_obj(2025, 1, 4),
                title="중복 일기",
                weather_data=None,
                emotion="sad",
                notes="",
            )
