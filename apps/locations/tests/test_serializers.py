from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from apps.locations.models import FavoriteLocation
from apps.locations.serializers import FavoriteLocationSerializer

User = get_user_model()


class FavoriteLocationSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="1234")
        # request 없이 serializer.context["request"].user 접근을 위해 간단한 더미
        self.req = type("Req", (), {"user": self.user})

    def test_create_first_favorite_assign_order_zero(self):
        """첫 즐겨찾기 생성 시 order=0 자동 할당"""
        serializer = FavoriteLocationSerializer(
            data={"city": "Seoul", "district": "Gangnam-gu"},
            context={"request": self.req},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.order, 0)

    def test_limit_exceeded(self):
        """즐겨찾기 3개 초과 시 limit_exceeded 에러 발생"""
        for i in range(3):
            FavoriteLocation.objects.create(
                user=self.user, city=f"City{i}", district=f"District{i}", order=i
            )

        serializer = FavoriteLocationSerializer(
            data={"city": "Seoul", "district": "Gangnam-gu"},
            context={"request": self.req},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(ValidationError) as cm:
            serializer.save()

        err = cm.exception.detail
        self.assertEqual(err.get("error"), "limit_exceeded")

    def test_duplicate_raises_already_exists(self):
        """동일 지역 중복 등록 시 already_exists 에러 발생"""
        FavoriteLocation.objects.create(
            user=self.user, city="Seoul", district="Gangnam-gu", order=0
        )

        serializer = FavoriteLocationSerializer(
            data={"city": "Seoul", "district": "Gangnam-gu"},
            context={"request": self.req},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(ValidationError) as cm:
            serializer.save()

        err = cm.exception.detail
        self.assertEqual(err.get("error"), "already_exists")
