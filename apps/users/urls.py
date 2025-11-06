from django.urls import include, path

app_name = "users"

urlpatterns = [
    path("auth/", include("apps.users.auth_urls")),
    path("social/", include("apps.users.social_urls")),
]
