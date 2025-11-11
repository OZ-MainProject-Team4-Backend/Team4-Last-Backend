from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class FavoriteLocationViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="1234")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.url = "/api/locations/favorites/"

    def test_create_favorite(self):
        """즐겨찾기 생성 - 생성 시 order 0번 자동 배정"""
        pass

    def test_create_limit_exceeded(self):
        """즐겨찾기 3개 초과 시 limit_exceeded 에러"""
        pass

    def test_create_duplicate_location(self):
        """동일 지역 중복 등록 시 already_exists 에러"""
        pass

    def test_update_alias(self):
        """PATCH /favorites/{id} - 별칭 변경"""
        pass

    def test_update_alias_block_order(self):
        """PATCH /favorites/{id}에 order 들어오면 차단"""
        pass

    def test_delete_favorite_reorders(self):
        """삭제 시 order 자동 재정렬"""
        pass

    def test_reorder(self):
        """order 순서 재정렬"""
        pass
