# apps/users/urls.py

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
    SocialLinkView,
    SocialLoginView,
    SocialUnlinkView,
    UserDeleteView,
)

app_name = 'users'

urlpatterns = [
    # 닉네임 검증
    path("nickname/validate", NicknameValidateView.as_view(), name="nickname-validate"),
    # 이메일 인증
    path("email/send", EmailSendView.as_view(), name="email-send"),
    path("email/verify", EmailVerifyView.as_view(), name="email-verify"),
    # 회원가입 & 로그인
    path("signup", SignUpView.as_view(), name="signup"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    # 마이페이지 & 프로필
    path("me", MyPageView.as_view(), name="mypage"),
    path("me/update", ProfileUpdateView.as_view(), name="profile-update"),
    path(
        "me/email/verify", EmailChangeVerifyView.as_view(), name="email-change-verify"
    ),
    path("me/delete", UserDeleteView.as_view(), name="user-delete"),
    path("me/password", PasswordChangeView.as_view(), name="password-change"),
    # 소셜 로그인
    path("social/<str:provider>/login", SocialLoginView.as_view(), name="social-login"),
    path("social/<str:provider>/link", SocialLinkView.as_view(), name="social-link"),
    path(
        "social/<str:provider>/unlink", SocialUnlinkView.as_view(), name="social-unlink"
    ),
]
