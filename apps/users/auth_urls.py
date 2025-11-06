# apps/users/auth_urls.py
from django.urls import path

from .views import (
    EmailChangeVerifyView,
    EmailSendView,
    EmailVerifyView,
    LoginView,
    LogoutView,
    MyPageView,
    NicknameValidateView,
    PasswordChangeView,
    ProfileUpdateView,
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
    path('me', MyPageView.as_view(), name='me'),
    # 사용자 관련
    path('users/me', MyPageView.as_view(), name='users-me-get'),
    path('users/me', ProfileUpdateView.as_view(), name='users-me-update'),
    path('users/me/delete', UserDeleteView.as_view(), name='user-delete'),
    path(
        'users/me/email/verify',
        EmailChangeVerifyView.as_view(),
        name='email-change-verify',
    ),
    path('users/me/password', PasswordChangeView.as_view(), name='password-change'),
    path(
        'users/nickname/validate',
        NicknameValidateView.as_view(),
        name='users-nickname-validate',
    ),
]
