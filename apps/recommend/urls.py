from django.urls import path

from .views import (
    OutfitRecommendByCoordsView,
    OutfitRecommendByLocationView,
)

urlpatterns = [
    path("coords/", OutfitRecommendByCoordsView.as_view(), name="recommend_by_coords"),
    path(
        "location/",
        OutfitRecommendByLocationView.as_view(),
        name="recommend_by_location",
    ),
]
