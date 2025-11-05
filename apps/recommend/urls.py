from django.urls import path

from .views import OutfitRecommendByCoordsView, OutfitRecommendByLocationView

urlpatterns = [
    path(
        "outfit/coords", OutfitRecommendByCoordsView.as_view(), name="outfit-by-coords"
    ),
    path(
        "outfit/location",
        OutfitRecommendByLocationView.as_view(),
        name="outfit-by-location",
    ),
]
