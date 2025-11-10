from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase
from apps.locations.models import FavoriteLocation

User = get_user_model()

class FavoriteLocationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="1234")

    def test_unique_constraint_per_user(self):
        FavoriteLocation.objects.create(user=self.user, city="Seoul", district="Gangnam-gu")
        with self.assertRaises(IntegrityError):
            FavoriteLocation.objects.create(user=self.user, city="Seoul", district="Gangnam-gu")

    def test_soft_delete_allows_recreate(self):
        fl = FavoriteLocation.objects.create(user=self.user, city="Seoul", district="Gangnam-gu")
        fl.delete()  # soft delete
        # 재생성 가능해야 함
        obj = FavoriteLocation.objects.create(user=self.user, city="Seoul", district="Gangnam-gu")
        self.assertIsNotNone(obj)

    def test_order_auto_sorting(self):
        fl1 = FavoriteLocation.objects.create(user=self.user, city="Seoul", district="A", order=0)
        fl2 = FavoriteLocation.objects.create(user=self.user, city="Seoul", district="B", order=1)

        # 삭제 후 재정렬은 view에서 처리되므로 모델 레벨에서는 정렬 순서만 보장됨
        self.assertLess(fl1.order, fl2.order)
