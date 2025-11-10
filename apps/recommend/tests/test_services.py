from django.test import TestCase
from unittest.mock import patch

from apps.recommend.services.recommend_service import generate_outfit_recommend


class GenerateOutfitRecommendTests(TestCase):

    @patch("apps.recommend.services.recommend_service.get_weather_data")
    def test_freezing_weather_recommendation(self, mock_weather):
        """-3°C에서 방한 코디가 추천되는지 확인"""
        mock_weather.return_value = {"temperature": -3, "condition": "Clear"}
        result = generate_outfit_recommend(None, 37.5, 127.0)

        self.assertIn("패딩", result["rec_1"])
        self.assertIn("추천드려요", result["explanation"])
        self.assertTrue(result["rec_1"])
        self.assertTrue(result["explanation"])

    @patch("apps.recommend.services.recommend_service.get_weather_data")
    def test_hot_weather_recommendation(self, mock_weather):
        """31°C에서 시원한 코디가 추천되는지 확인"""
        mock_weather.return_value = {"temperature": 31, "condition": "Clear"}
        result = generate_outfit_recommend(None, 37.5, 127.0)

        self.assertIn("민소매", result["rec_1"])
        self.assertIn("시원한 소재", result["explanation"])
        self.assertTrue(result["rec_3"])

    @patch("apps.recommend.services.recommend_service.get_weather_data")
    def test_rain_condition_recommendation(self, mock_weather):
        """비 오는 날 방수 코디가 추천되는지 확인"""
        mock_weather.return_value = {"temperature": 22, "condition": "Rain"}
        result = generate_outfit_recommend(None, 37.5, 127.0)

        self.assertIn("비 오는", result["explanation"])
        self.assertIn("레인", result["rec_2"])
        self.assertTrue(result["rec_1"])
