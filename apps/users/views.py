import logging
import random
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount, Token
from .serializers import (
    EmailSendSerializer,
    EmailVerifySerializer,
    FavoriteRegionsSerializer,
    LoginSerializer,
    NicknameValidateSerializer,
    PasswordChangeSerializer,
    RefreshTokenSerializer,
    SignupSerializer,
    SocialLinkSerializer,
    SocialLoginSerializer,
    SocialUnlinkSerializer,
    UserDeleteSerializer,
    UserProfileSerializer,
)
from .services.social_auth_service import SocialAuthService
from .utils.send_email import send_verification_email
from .utils.social_auth import (
    SocialTokenInvalidError,
    verify_social_token,
)

User = get_user_model()
logger = logging.getLogger(__name__)

# ============ Constants ============
EMAIL_VERIF_CODE_TTL = 300
EMAIL_PREVER_TTL = 1800
EMAIL_VERIF_RESEND_TTL = 60
EMAIL_VERIF_MAX_PER_HOUR = 5


# ============ Helpers ============
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


def gen_code(n=6):
    return "".join(str(random.randint(0, 9)) for _ in range(n))


def key_verif(email: str):
    return f"email_verif:{email.lower()}"


def key_preverified(email: str):
    return f"email_preverified:{email.lower()}"


def key_resend(email: str):
    return f"email_verif_resend:{email.lower()}"


def key_count(email: str):
    return f"email_verif_count:{email.lower()}"


def key_nickname_valid(nickname: str):
    return f"nickname_valid:{nickname.lower()}"


def create_jwt_token(user):
    """JWT 토큰 생성 및 DB 저장"""
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    Token.objects.update_or_create(
        user=user,
        defaults={
            "access_jwt": access_token,
            "refresh_jwt": refresh_token,
            "access_expires_at": timezone.now() + timedelta(minutes=15),
            "refresh_expires_at": timezone.now() + timedelta(days=7),
            "revoked": False,
        },
    )
    return access_token, refresh_token


def get_user_data(user):
    """사용자 데이터 포맷팅"""
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "gender": getattr(user, "gender", None),
        "age_group": getattr(user, "age_group", None),
        "is_verified": user.email_verified,
        "created_at": (
            user.created_at.isoformat() if hasattr(user, "created_at") else None
        ),
    }


def set_refresh_token_cookie(response, refresh_token):
    """Refresh Token을 HttpOnly 쿠키로 설정"""
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=getattr(settings, 'SECURE_COOKIES', True),  # HTTPS 환경에서만 전송
        samesite='Lax',
        max_age=7 * 24 * 60 * 60,  # 7일
    )


# ============ Auth Views ============
class NicknameValidateView(APIView):
    permission_classes = [AllowAny]
    serializer_class = NicknameValidateSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data["nickname"].strip()

        if User.objects.filter(
            nickname__iexact=nickname, deleted_at__isnull=True
        ).exists():
            return error_response(
                "nickname_already_in_use",
                "이미 사용 중인 닉네임입니다",
                status.HTTP_400_BAD_REQUEST,
            )

        cache.set(key_nickname_valid(nickname), True, timeout=300)
        return success_response("닉네임 사용가능", status_code=200)


class EmailSendView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailSendSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        if User.objects.filter(
            email__iexact=email, email_verified=True, deleted_at__isnull=True
        ).exists():
            return error_response(
                "email_already_verified",
                "이미 인증이 된 이메일",
                status.HTTP_400_BAD_REQUEST,
            )

        if cache.get(key_resend(email)):
            return error_response(
                "email_resend_limit", "재전송 제한", status.HTTP_429_TOO_MANY_REQUESTS
            )

        cnt_key = key_count(email)
        cnt = cache.get(cnt_key) or 0
        if cnt >= EMAIL_VERIF_MAX_PER_HOUR:
            return error_response(
                "email_send_limit", "발송 초과", status.HTTP_429_TOO_MANY_REQUESTS
            )

        cache.incr(cnt_key) if cnt else cache.set(cnt_key, 1, timeout=3600)

        code = gen_code(6)
        cache.set(key_verif(email), code, timeout=EMAIL_VERIF_CODE_TTL)
        cache.set(key_resend(email), 1, timeout=EMAIL_VERIF_RESEND_TTL)

        try:
            send_verification_email(email, code)
        except Exception as e:
            cache.delete(key_verif(email))
            cache.delete(key_resend(email))
            logger.exception(f"Email send failed: {str(e)}")
            return error_response(
                "email_send_failed",
                "메일 발송 실패",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return success_response("인증 코드 발송완료", status_code=200)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailVerifySerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"].strip()

        cached = cache.get(key_verif(email))
        if not cached or cached != code:
            return error_response(
                "code_invalid_or_expired",
                "코드 만료 또는 불일치",
                status.HTTP_400_BAD_REQUEST,
            )

        cache.delete(key_verif(email))
        cache.set(key_preverified(email), True, timeout=EMAIL_PREVER_TTL)
        return success_response("이메일 인증 완료", status_code=200)


class SignUpView(APIView):
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email").strip().lower()

        if not cache.get(key_preverified(email)):
            return error_response(
                "email_not_verified", "이메일 미검증", status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email__iexact=email, deleted_at__isnull=True).exists():
            return error_response(
                "email_duplicate", "이메일 중복", status.HTTP_400_BAD_REQUEST
            )

        nickname = serializer.validated_data.get("nickname")
        if (
            nickname
            and User.objects.filter(
                nickname__iexact=nickname, deleted_at__isnull=True
            ).exists()
        ):
            return error_response(
                "nickname_duplicate", "닉네임 중복", status.HTTP_400_BAD_REQUEST
            )

        user = serializer.create(serializer.validated_data)
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        cache.delete(key_preverified(email))

        return success_response(
            "회원가입 완료",
            data={"user": get_user_data(user)},
            status_code=201,
            http_status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if not getattr(user, "email_verified", False):
            return error_response(
                "email_not_verified", "이메일 인증 필요", status.HTTP_401_UNAUTHORIZED
            )

        if not getattr(user, "is_active", True) or getattr(user, "deleted_at", None):
            return error_response(
                "account_inactive",
                "비활성한 계정이거나 탈퇴 계정입니다",
                status.HTTP_403_FORBIDDEN,
            )

        access, refresh = create_jwt_token(user)

        response = success_response(
            "로그인 성공",
            data={"user": get_user_data(user), "access": access},
            status_code=200,
        )

        # Refresh token을 HttpOnly 쿠키로 설정
        set_refresh_token_cookie(response, refresh)

        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.revoked = True
            token.save(update_fields=["revoked"])

            response = success_response("로그아웃 완료", status_code=200)
            # Refresh token 쿠키 삭제
            response.delete_cookie('refresh_token')

            return response
        except Token.DoesNotExist:
            return error_response(
                "token_not_found", "토큰을 찾을 수 없습니다", status.HTTP_404_NOT_FOUND
            )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RefreshTokenSerializer

    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(
            'refresh_token'
        )

        if not refresh_token:
            return error_response(
                "refresh_token_required",
                "Refresh 토큰이 필요합니다",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            user_id = refresh.get("user_id")

            token = Token.objects.get(user_id=user_id, revoked=False)
            token.access_jwt = new_access_token
            token.access_expires_at = timezone.now() + timedelta(minutes=15)
            token.save(update_fields=["access_jwt", "access_expires_at"])

            # 새로운 refresh token 생성 (선택사항: Refresh Token Rotation)
            new_refresh = RefreshToken.for_user_id(user_id)
            new_refresh_token = str(new_refresh)

            token.refresh_jwt = new_refresh_token
            token.refresh_expires_at = timezone.now() + timedelta(days=7)
            token.save(update_fields=["refresh_jwt", "refresh_expires_at"])

            response = success_response(
                "토큰 갱신 완료", data={"access": new_access_token}, status_code=200
            )

            # 새로운 refresh token을 쿠키로 설정
            set_refresh_token_cookie(response, new_refresh_token)

            return response
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return error_response(
                "invalid_refresh_token",
                "유효하지 않은 Refresh 토큰",
                status.HTTP_401_UNAUTHORIZED,
            )


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
            pending_key = f"email_change_pending:{user.id}:{new_email.strip().lower()}"
            code = gen_code(6)
            cache.set(pending_key, code, timeout=EMAIL_PREVER_TTL)
            try:
                send_verification_email(new_email, code)
            except Exception as e:
                cache.delete(pending_key)
                logger.exception(f"Email send failed: {str(e)}")
                return error_response(
                    "email_send_failed",
                    "메일 발송 실패",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
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
        user.favorite_regions = regions
        user.updated_at = timezone.now()
        user.save(update_fields=["favorite_regions", "updated_at"])
        return success_response(
            "즐겨찾는 지역 수정 완료",
            data={"favorite_regions": regions},
            status_code=200,
        )


class EmailChangeVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        new_email = (request.data.get("email") or "").strip().lower()
        code = (request.data.get("code") or "").strip()

        if not new_email or not code:
            return error_response(
                "validation_failed",
                "email과 인증코드가 필요합니다",
                status.HTTP_400_BAD_REQUEST,
            )

        pending_key = f"email_change_pending:{user.id}:{new_email}"
        cached = cache.get(pending_key)
        if not cached or cached != code:
            return error_response(
                "code_invalid_or_expired",
                "코드 만료 또는 불일치",
                status.HTTP_400_BAD_REQUEST,
            )

        user.email = new_email
        user.email_verified = True
        user.save(update_fields=["email", "email_verified"])
        cache.delete(pending_key)
        return success_response(
            "이메일 변경 완료", data={"user": get_user_data(user)}, status_code=200
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
        if user.deleted_at:
            return error_response(
                "already_deleted", "이미 탈퇴한 계정입니다", status.HTTP_400_BAD_REQUEST
            )

        user.deleted_at = timezone.now()
        user.is_active = False
        user.save(update_fields=["deleted_at", "is_active"])
        logger.info(f"User deleted: {user.email}")

        response = success_response(
            "회원탈퇴 완료", data={"deleted": True}, status_code=200
        )
        # 탈퇴 시 쿠키 삭제
        response.delete_cookie('refresh_token')

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

        try:
            social_user_info = verify_social_token(
                provider, serializer.validated_data["token"]
            )
            user = SocialAuthService.get_or_create_user_from_social(
                provider, social_user_info
            )

            if user.deleted_at or not user.is_active:
                return error_response(
                    "account_inactive", "비활성 계정", status.HTTP_403_FORBIDDEN
                )

            access, refresh = create_jwt_token(user)
            logger.info(f"Social login success: {provider} - {user.email}")

            response = success_response(
                "로그인 성공",
                data={
                    "user": get_user_data(user),
                    "access": access,
                },
                status_code=200,
            )

            # Refresh token을 HttpOnly 쿠키로 설정
            set_refresh_token_cookie(response, refresh)

            return response
        except SocialTokenInvalidError:
            return error_response(
                "token_invalid", "소셜 인증 실패", status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.exception(f"Social login error: {str(e)}")
            return error_response(
                "internal_error",
                "로그인 처리 중 오류가 발생했습니다",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SocialCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return redirect("http://localhost:3000/login/failed")

        config = settings.SOCIAL_PROVIDERS[provider]
        code = request.GET.get("code")

        if not code:
            return redirect("http://localhost:3000/login/failed")

        try:
            token_data = {
                "grant_type": "authorization_code",
                "client_id": config["client_id"],
                "client_secret": config.get("client_secret"),
                "code": code,
                "redirect_uri": config["redirect_uri"],
            }

            token_response = requests.post(
                config["token_url"], data=token_data, timeout=5
            )
            if token_response.status_code != 200:
                return redirect("http://localhost:3000/login/failed")

            access_token = token_response.json().get("access_token")
            user_info_response = requests.get(
                config["user_info_url"],
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )

            if user_info_response.status_code != 200:
                return redirect("http://localhost:3000/login/failed")

            user_data = user_info_response.json()
            social_user_info = self._parse_social_user(provider, user_data)
            user = SocialAuthService.get_or_create_user_from_social(
                provider, social_user_info
            )

            if user.deleted_at or not user.is_active:
                return redirect("http://localhost:3000/login/failed")

            access, refresh = create_jwt_token(user)
            logger.info(f"Social callback success: {provider} - {user.email}")
            response = redirect(f"http://localhost:3000/login/success?access={access}")
            set_refresh_token_cookie(response, refresh)

            return response
        except Exception as e:
            logger.exception(f"Social callback error: {str(e)}")
            return redirect("http://localhost:3000/login/failed")

    @staticmethod
    def _parse_social_user(provider, user_data):
        if provider == "kakao":
            return {
                "provider_user_id": str(user_data["id"]),
                "email": user_data.get("kakao_account", {}).get("email"),
                "nickname": user_data.get("properties", {}).get("nickname"),
            }
        elif provider == "naver":
            resp = user_data.get("response", {})
            return {
                "provider_user_id": resp.get("id"),
                "email": resp.get("email"),
                "nickname": resp.get("nickname") or resp.get("name"),
            }
        else:  # google
            return {
                "provider_user_id": user_data.get("id"),
                "email": user_data.get("email"),
                "nickname": user_data.get("name"),
            }


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

        try:
            social_user_info = verify_social_token(
                provider, serializer.validated_data["token"]
            )
            SocialAuthService.link_social_account(
                request.user, provider, social_user_info
            )
            logger.info(f"Social account linked: {provider} - {request.user.email}")
            return success_response("소셜 계정 연결 완료", status_code=200)
        except SocialTokenInvalidError:
            return error_response(
                "token_invalid", "소셜 인증 실패", status.HTTP_401_UNAUTHORIZED
            )
        except ValueError as e:
            return error_response("validation_failed", str(e), status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.exception(f"Social link error: {str(e)}")
            return error_response(
                "internal_error",
                "계정 연결 중 오류가 발생했습니다",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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

        try:
            SocialAuthService.unlink_social_account(request.user, provider)
            logger.info(f"Social account unlinked: {provider} - {request.user.email}")
            return success_response("소셜 계정 해제 완료", status_code=200)
        except SocialAccount.DoesNotExist:
            return error_response(
                "social_account_not_found",
                "연결된 소셜 계정 없음",
                status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception(f"Social unlink error: {str(e)}")
            return error_response(
                "internal_error",
                "계정 연결 해제 중 오류가 발생했습니다",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
