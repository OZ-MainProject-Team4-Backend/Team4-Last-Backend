# apps/users/auth_urls.py
from django.urls import path

from .views import (
    EmailChangeVerifyView,
    EmailSendView,
    EmailVerifyView,
    FavoriteRegionsUpdateView,
    LoginView,
    LogoutView,
    MyPageView,
    NicknameValidateView,
    PasswordChangeView,
    ProfileUpdateView,
    RefreshTokenView,  # ← 추가
    SignUpView,
    UserDeleteView,
)

app_name = 'users_auth'

urlpatterns = [
    # 인증 관련
    path('nickname/validate', NicknameValidateView.as_view(), name='nickname-validate'),
    path('email/send', EmailSendView.as_view(), name='email-send'),
    path('email/verify', EmailVerifyView.as_view(), name='email-verify'),
    path('signup', SignUpView.as_view(), name='signup'),
    path('login', LoginView.as_view(), name='login'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('refresh', RefreshTokenView.as_view(), name='refresh'),  # ← 추가
    # 사용자 관련
    path('me', MyPageView.as_view(), name='me'),
    path('profile', ProfileUpdateView.as_view(), name='profile-update'),
    path(
        'profile/regions', FavoriteRegionsUpdateView.as_view(), name='favorite-regions'
    ),
    path(
        'email/verify-change',
        EmailChangeVerifyView.as_view(),
        name='email-change-verify',
    ),
    path('password', PasswordChangeView.as_view(), name='password-change'),
    path('user', UserDeleteView.as_view(), name='user-delete'),
]