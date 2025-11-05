from rest_framework.routers import DefaultRouter

from .views import FavoriteLocationViewSet

router = DefaultRouter()
router.register(r"favorites", FavoriteLocationViewSet, basename="favorite-locations")

urlpatterns = router.urls
