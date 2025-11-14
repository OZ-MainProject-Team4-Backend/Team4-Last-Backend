from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.locations.models import FavoriteLocation

User = get_user_model()


class FavoriteLocationViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="1234")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/locations/favorites/"

    def test_create_favorite(self):
        """즐겨찾기 생성 - 생성 시 order 0번 자동 배정"""
        data = {"city": "Seoul", "district": "Gangnam-gu", "alias": "본가"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "즐겨찾기에 추가되었습니다.")
        self.assertEqual(FavoriteLocation.objects.count(), 1)
        self.assertEqual(FavoriteLocation.objects.first().order, 0)

    def test_create_limit_exceeded(self):
        """즐겨찾기 3개 초과 시 400 limit_exceeded 에러"""
        for i in range(3):
            FavoriteLocation.objects.create(
                user=self.user, city=f"City{i}", district=f"District{i}", order=i
            )

        data = {"city": "Busan", "district": "Haeundae-gu"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "limit_exceeded")

    def test_create_duplicate_location(self):
        """동일 지역 중복 등록 시 409 already_exists 에러"""
        FavoriteLocation.objects.create(
            user=self.user, city="Seoul", district="Gangnam-gu", order=0
        )

        data = {"city": "Seoul", "district": "Gangnam-gu"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "already_exists")

    def test_update_alias(self):
        """PATCH /favorites/{id} - 별칭 변경"""
        fav = FavoriteLocation.objects.create(
            user=self.user, city="Seoul", district="Gangnam-gu", alias="집", order=0
        )

        response = self.client.patch(
            f"{self.url}{fav.id}/", {"alias": "본가"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "즐겨찾기 정보가 수정되었습니다.")

        fav.refresh_from_db()
        self.assertEqual(fav.alias, "본가")

    def test_update_alias_block_order(self):
        """PATCH /favorites/{id}에 order 들어오면 차단"""
        fav = FavoriteLocation.objects.create(
            user=self.user, city="Seoul", district="Gangnam-gu", alias="집", order=0
        )

        response = self.client.patch(
            f"{self.url}{fav.id}/", {"order": 2}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "order_not_allowed_here")

    def test_delete_favorite_reorders(self):
        """삭제 시 order 자동 재정렬"""
        fav1 = FavoriteLocation.objects.create(
            user=self.user, city="A", district="A", order=0
        )
        fav2 = FavoriteLocation.objects.create(
            user=self.user, city="B", district="B", order=1
        )
        fav3 = FavoriteLocation.objects.create(
            user=self.user, city="C", district="C", order=2
        )

        # 중간(2번 자리)인 fav2 삭제
        response = self.client.delete(f"{self.url}{fav2.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        fav1.refresh_from_db()
        fav3.refresh_from_db()

        # 재정렬되었는지 확인
        self.assertEqual(fav1.order, 0)
        self.assertEqual(fav3.order, 1)

    def test_reorder(self):
        """order 순서 재정렬"""
        fav1 = FavoriteLocation.objects.create(
            user=self.user, city="A", district="A", order=0
        )
        fav2 = FavoriteLocation.objects.create(
            user=self.user, city="B", district="B", order=1
        )
        fav3 = FavoriteLocation.objects.create(
            user=self.user, city="C", district="C", order=2
        )

        new_order = [
            {"id": fav3.id, "order": 0},
            {"id": fav1.id, "order": 1},
            {"id": fav2.id, "order": 2},
        ]

        response = self.client.patch(self.url + "reorder/", new_order, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "즐겨찾기 순서가 변경되었습니다.")

        fav1.refresh_from_db()
        fav2.refresh_from_db()
        fav3.refresh_from_db()

        self.assertEqual(fav3.order, 0)
        self.assertEqual(fav1.order, 1)
        self.assertEqual(fav2.order, 2)
