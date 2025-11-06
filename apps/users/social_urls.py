from django.urls import path

from .views import (
    SocialCallbackView,
    SocialLinkView,
    SocialLoginView,
    SocialUnlinkView,
)

app_name = "users_social"

urlpatterns = [
    path('<str:provider>/login', SocialLoginView.as_view(), name='social-login'),
    path(
        '<str:provider>/callback', SocialCallbackView.as_view(), name='social-callback'
    ),
    path('<str:provider>/link', SocialLinkView.as_view(), name='social-link'),
    path('<str:provider>/unlink', SocialUnlinkView.as_view(), name='social-unlink'),
]
