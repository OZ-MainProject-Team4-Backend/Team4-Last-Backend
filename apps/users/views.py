import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SocialAccount
from .serializers import (
    EmailSendSerializer,
    EmailVerifySerializer,
    FavoriteRegionsSerializer,
    LoginSerializer,
    NicknameValidateSerializer,
    PasswordChangeSerializer,
    SignupSerializer,
    SocialLinkSerializer,
    SocialLoginSerializer,
    SocialUnlinkSerializer,
    UserDeleteSerializer,
    UserProfileSerializer,
)
from .services.auth_service import (
    delete_user_service,
    email_change_service,
    handle_login,
    logout_user_service,
    refresh_token_service,
    send_email_verification_service,
    signup_user_service,
    social_callback_service,
    social_link_service,
    social_login_service,
    social_unlink_service,
    update_favorite_regions_service,
    validate_nickname_service,
    verify_email_change_service,
    verify_email_code_service,
)
from .services.token_service import create_jwt_pair_for_user
from .services.social_auth_service import SocialAuthService
from .utils.auth_utils import get_user_data

User = get_user_model()
logger = logging.getLogger(__name__)


# ============ Helper Functions ============
def success_response(
    message: str, data=None, status_code=200, http_status=status.HTTP_200_OK
):
    return Response(
        (
            {
                "success": True,
                "statusCode": status_code,
                "message": message,
                "data": data,
            }
            if data
            else {
                "success": True,
                "statusCode": status_code,
                "message": message,
            }
        ),
        status=http_status,
    )


def error_response(
    code: str, message: str, http_status=status.HTTP_400_BAD_REQUEST, status_code=None
):
    status_code_map = {
        status.HTTP_400_BAD_REQUEST: 400,
        status.HTTP_401_UNAUTHORIZED: 401,
        status.HTTP_403_FORBIDDEN: 403,
        status.HTTP_404_NOT_FOUND: 404,
        status.HTTP_429_TOO_MANY_REQUESTS: 429,
        status.HTTP_500_INTERNAL_SERVER_ERROR: 500,
    }
    return Response(
        {
            "success": False,
            "statusCode": status_code or status_code_map.get(http_status, 400),
            "error": {"code": code, "message": message},
        },
        status=http_status,
    )


def set_refresh_token_cookie(response, refresh_token, is_auto_login=False):
    """Refresh Token을 HttpOnly 쿠키로 설정"""
    cookie_params = {
        "key": "refresh",
        "value": refresh_token,
        "httponly": True,
        "secure": getattr(settings, 'SECURE_COOKIES', True),
        "samesite": "Strict",
    }

    if is_auto_login:
        cookie_params["max_age"] = 7 * 24 * 60 * 60

    response.set_cookie(**cookie_params)


# ============ Auth Views ============
class NicknameValidateView(APIView):
    permission_classes = [AllowAny]
    serializer_class = NicknameValidateSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data["nickname"].strip()

        success, code, message, http_status = validate_nickname_service(nickname)
        if not success:
            return error_response(code, message, http_status)

        return success_response("닉네임 사용가능", status_code=200)


class EmailSendView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailSendSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        success, code, message, http_status = send_email_verification_service(email)
        if not success:
            return error_response(code, message, http_status)

        return success_response("인증 코드 발송완료", status_code=200)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailVerifySerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"].strip()

        success, error_code, error_message, http_status = verify_email_code_service(email, code)
        if not success:
            return error_response(error_code, error_message, http_status)

        return success_response("이메일 인증 완료", status_code=200)


class SignUpView(APIView):
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, user_data, error_code, error_message, http_status = signup_user_service(serializer.validated_data)
        if not success:
            return error_response(error_code, error_message, http_status)

        return success_response(
            "회원가입 완료",
            data={"user": user_data},
            status_code=http_status,
            http_status=http_status,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        is_auto_login = serializer.validated_data["isAutoLogin"]

        login_data = handle_login(user, is_auto_login)

        response = success_response(
            "로그인 성공",
            data=login_data["serialized_data"],
            status_code=200,
        )

        set_refresh_token_cookie(response, login_data["refresh_token"], is_auto_login)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout_user_service(request.user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("refresh")
        return response


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token_value = request.data.get("refresh") or request.COOKIES.get("refresh")

        success, new_access_token, access_expires_at, new_refresh_token, is_auto_login, error_code, error_message, http_status = refresh_token_service(refresh_token_value)

        if not success:
            return error_response(error_code, error_message, http_status)

        response = success_response(
            "토큰 갱신 완료",
            data={
                "access": new_access_token,
                "access_expires_at": access_expires_at,
            },
            status_code=200,
        )

        set_refresh_token_cookie(response, new_refresh_token, is_auto_login)
        return response


# ============ User Views ============
class MyPageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return success_response(
            "",
            data={
                **get_user_data(u),
                "favorite_regions": getattr(u, "favorite_regions", None) or [],
            },
            status_code=200,
        )


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def patch(self, request):
        user = request.user
        serializer = self.serializer_class(
            instance=user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        new_email = serializer.validated_data.get("email")
        if new_email and new_email.strip().lower() != user.email.lower():
            success, error_code, error_message, http_status = email_change_service(user, new_email)
            if not success:
                return error_response(error_code, error_message, http_status)
            return success_response("이메일 변경 인증 코드 발송 완료", status_code=200)

        serializer.save()
        user.updated_at = timezone.now()
        user.save(update_fields=["updated_at"])
        return success_response("프로필 수정 완료", status_code=200)


class FavoriteRegionsUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteRegionsSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        regions = serializer.validated_data["favorite_regions"]

        success, updated_regions, error_code, error_message, http_status = update_favorite_regions_service(user, regions)
        if not success:
            return error_response(error_code, error_message, http_status)

        return success_response(
            "즐겨찾는 지역 수정 완료",
            data={"favorite_regions": updated_regions},
            status_code=200,
        )


class EmailChangeVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        new_email = (request.data.get("email") or "").strip().lower()
        code = (request.data.get("code") or "").strip()

        success, user_data, error_code, error_message, http_status = verify_email_change_service(user, new_email, code)
        if not success:
            return error_response(error_code, error_message, http_status)

        return success_response(
            "이메일 변경 완료", data={"user": user_data}, status_code=200
        )


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    def patch(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response("비밀번호 변경 완료", status_code=200)


class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDeleteSerializer

    def delete(self, request):
        user = request.user

        success, error_code, error_message, http_status = delete_user_service(user)
        if not success:
            return error_response(error_code, error_message, http_status)

        response = success_response(
            "회원탈퇴 완료", data={"deleted": True}, status_code=200
        )
        response.delete_cookie("refresh")
        return response


# ============ Social Views ============
class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = SocialLoginSerializer

    def post(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return error_response(
                "invalid_provider",
                "지원하지 않는 소셜 로그인",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_auto_login = request.data.get("isAutoLogin", False)
        token = serializer.validated_data["token"]

        success, response_data, error_code, error_message, http_status = social_login_service(provider, token, is_auto_login)
        if not success:
            return error_response(error_code, error_message, http_status)

        response = success_response(
            "로그인 성공",
            data=response_data,
            status_code=200,
        )

        set_refresh_token_cookie(response, response_data["refresh"], is_auto_login)
        return response


class SocialCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return redirect("http://localhost:3000/login/failed")

        config = settings.SOCIAL_PROVIDERS[provider]
        code = request.GET.get("code")

        success, response_data, error_code, error_message = social_callback_service(provider, code, config)
        if not success:
            return redirect("http://localhost:3000/login/failed")

        response = redirect(
            f"http://localhost:3000/login/success?access={response_data['access']}"
        )
        set_refresh_token_cookie(response, response_data["refresh"], is_auto_login=False)
        return response


class SocialLinkView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SocialLinkSerializer

    def post(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return error_response(
                "invalid_provider",
                "지원하지 않는 소셜 로그인",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        success, error_code, error_message, http_status = social_link_service(request.user, provider, token)
        if not success:
            return error_response(error_code, error_message, http_status)

        return success_response("소셜 계정 연결 완료", status_code=200)


class SocialUnlinkView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SocialUnlinkSerializer

    def delete(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return error_response(
                "invalid_provider",
                "지원하지 않는 소셜 로그인",
                status.HTTP_400_BAD_REQUEST,
            )

        success, error_code, error_message, http_status = social_unlink_service(request.user, provider)
        if not success:
            return error_response(error_code, error_message, http_status)

        return success_response("소셜 계정 해제 완료", status_code=200)