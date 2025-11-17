"""
URL configuration for apps project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import permissions

urlpatterns = [
    # path('', RedirectView.as_view(url='/api/schema/swagger-ui/', permanent=False)),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[permissions.AllowAny]),
        name="schema",
    ),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            permission_classes=[permissions.AllowAny],
        ),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema",
            permission_classes=[permissions.AllowAny],
        ),
        name="redoc",
    ),
    # Admin
    path("admin/", admin.site.urls),
    # API Routes
    path("api/auth/", include("apps.users.auth_urls")),
    path("api/social/", include("apps.users.social_urls")),
    path("api/locations/", include("apps.locations.urls")),
    path("api/weather/", include("apps.weather.urls")),
    path("api/diary/", include("apps.diary.urls")),
    path("api/recommend/", include("apps.recommend.urls"), name="recommend"),
    path("api/chat/", include("apps.chat.urls"), name="chat"),
]
