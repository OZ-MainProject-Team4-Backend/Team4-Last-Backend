import logging
import random
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SocialAccount
from .serializers import (
    EmailSendSerializer,
    EmailVerifySerializer,
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
from .services.social_auth_service import SocialAuthService
from .utils.send_email import send_verification_email
from .utils.social_auth import (
    SocialProviderNotFoundError,
    SocialTokenInvalidError,
    verify_social_token,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def key_verif(email: str) -> str:
    return f"email_verif:{email.lower()}"


def key_preverified(email: str) -> str:
    return f"email_preverified:{email.lower()}"


def key_resend(email: str) -> str:
    return f"email_verif_resend:{email.lower()}"


def key_count(email: str) -> str:
    return f"email_verif_count:{email.lower()}"


def key_nickname_valid(nickname: str) -> str:
    return f"nickname_valid:{nickname.lower()}"


EMAIL_VERIF_CODE_TTL = 300
EMAIL_PREVER_TTL = 1800
EMAIL_VERIF_RESEND_TTL = 60
EMAIL_VERIF_MAX_PER_HOUR = 5


def gen_code(n=6) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(n))


class NicknameValidateView(APIView):
    permission_classes = [AllowAny]
    serializer_class = NicknameValidateSerializer

    @extend_schema(request=NicknameValidateSerializer, responses={200: dict})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data["nickname"].strip()

        if User.objects.filter(
            nickname__iexact=nickname, deleted_at__isnull=True
        ).exists():
            return Response(
                {"error": "이미 사용 중인 닉네임입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache.set(key_nickname_valid(nickname), True, timeout=300)
        return Response({"message": "닉네임 사용가능"}, status=status.HTTP_200_OK)


class EmailSendView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailSendSerializer

    @extend_schema(request=EmailSendSerializer, responses={200: dict})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        if User.objects.filter(
            email__iexact=email, email_verified=True, deleted_at__isnull=True
        ).exists():
            return Response(
                {"error": "이미 인증이 된 이메일"}, status=status.HTTP_400_BAD_REQUEST
            )

        if cache.get(key_resend(email)):
            return Response(
                {"error": "재전송 제한"}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        cnt_key = key_count(email)
        cnt = cache.get(cnt_key) or 0
        if cnt >= EMAIL_VERIF_MAX_PER_HOUR:
            return Response(
                {"error": "발송 초과"}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        if cnt:
            cache.incr(cnt_key)
        else:
            cache.set(cnt_key, 1, timeout=3600)

        code = gen_code(6)
        cache.set(key_verif(email), code, timeout=EMAIL_VERIF_CODE_TTL)
        cache.set(key_resend(email), 1, timeout=EMAIL_VERIF_RESEND_TTL)

        try:
            send_verification_email(email, code)
        except Exception as e:
            cache.delete(key_verif(email))
            cache.delete(key_resend(email))
            return Response(
                {"error": "메일 발송 실패", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"message": "인증 코드 발송완료"}, status=status.HTTP_200_OK)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailVerifySerializer

    @extend_schema(request=EmailVerifySerializer, responses={200: dict})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"].strip()

        cached = cache.get(key_verif(email))
        if not cached or cached != code:
            return Response(
                {"error": "코드 만료 또는 불일치"}, status=status.HTTP_400_BAD_REQUEST
            )

        cache.delete(key_verif(email))
        cache.set(key_preverified(email), True, timeout=EMAIL_PREVER_TTL)
        return Response({"message": "이메일 인증 완료"}, status=status.HTTP_200_OK)


class SignUpView(APIView):
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer

    @extend_schema(request=SignupSerializer, responses={201: dict})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email").strip().lower()

        if not cache.get(key_preverified(email)):
            return Response(
                {"error": "이메일 미검증"}, status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email__iexact=email, deleted_at__isnull=True).exists():
            return Response(
                {"error": "이메일 중복"}, status=status.HTTP_400_BAD_REQUEST
            )

        nickname = serializer.validated_data.get("nickname")
        if (
            nickname
            and User.objects.filter(
                nickname__iexact=nickname, deleted_at__isnull=True
            ).exists()
        ):
            return Response(
                {"error": "닉네임 중복"}, status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.create(serializer.validated_data)
        user.email_verified = True
        user.save(update_fields=["email_verified"])

        cache.delete(key_preverified(email))

        login(request, user)

        return Response(
            {
                "message": "회원가입 완료",
                "user": {"email": user.email, "nickname": user.nickname},
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(request=LoginSerializer, responses={200: dict})
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        if not getattr(user, "email_verified", False):
            return Response(
                {"error": "이메일 인증 필요"}, status=status.HTTP_401_UNAUTHORIZED
            )

        if not getattr(user, "is_active", True) or getattr(user, "deleted_at", None):
            return Response(
                {"error": "비활성한 계정이거나 탈퇴 계정입니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request, user)
        return Response(
            {
                "message": "로그인 성공",
                "user": {"email": user.email, "nickname": user.nickname},
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    @extend_schema(responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyPageView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        u = request.user
        data = {
            "id": u.id,
            "email": u.email,
            "nickname": u.nickname,
            "gender": u.gender,
            "age_group": u.age_group,  # 또는 age로 변경
        }
        return Response(data, status=status.HTTP_200_OK)


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(request=UserProfileSerializer, responses={200: dict})
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
                return Response(
                    {"error": "메일 발송 실패", "detail": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(
                {"message": "이메일 변경 인증 코드 발송 완료"},
                status=status.HTTP_200_OK,
            )

        serializer.save()
        user.updated_at = timezone.now()
        user.save(update_fields=["updated_at"])
        return Response({"message": "프로필 수정 완료"}, status=status.HTTP_200_OK)


class EmailChangeVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=EmailVerifySerializer, responses={200: dict})
    def post(self, request):
        user = request.user
        new_email = (request.data.get("email") or "").strip().lower()
        code = (request.data.get("code") or "").strip()

        if not new_email or not code:
            return Response(
                {"error": "email과 인증코드가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending_key = f"email_change_pending:{user.id}:{new_email}"
        cached = cache.get(pending_key)
        if not cached or cached != code:
            return Response(
                {"error": "코드 만료 또는 불일치"}, status=status.HTTP_400_BAD_REQUEST
            )

        user.email = new_email
        user.email_verified = True
        user.save(update_fields=["email", "email_verified"])
        cache.delete(pending_key)
        return Response({"message": "이메일 변경 완료"}, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    @extend_schema(request=PasswordChangeSerializer, responses={200: dict})
    def patch(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "비밀번호 변경 완료"}, status=status.HTTP_200_OK)


class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDeleteSerializer

    @extend_schema(request=UserDeleteSerializer, responses={200: dict})
    def delete(self, request):
        user = request.user

        if user.deleted_at:
            return Response(
                {"error": "이미 탈퇴한 계정입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.deleted_at = timezone.now()
        user.is_active = False
        user.save(update_fields=["deleted_at", "is_active"])

        logout(request)

        logger.info(f"User deleted: {user.email}")

        return Response({"deleted": True}, status=status.HTTP_200_OK)


class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = SocialLoginSerializer

    def get(self, request, provider):
        # provider 유효성 검사
        if provider not in settings.SOCIAL_PROVIDERS:
            return Response({"error": "지원하지 않는 소셜 로그인"}, status=400)

        config = settings.SOCIAL_PROVIDERS[provider]
        # 기본 파라미터들 (provider 설정에 따라 이름과 required가 다름)
        # 예시: kakao(카카오) -> authorize_url, client_id, redirect_uri, response_type=code
        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
        }

        # provider 별 추가 파라미터 (예: kakao state, scope 등)
        # 상태 검증을 위해 state 생성해 세션에 넣어두기 (naver는 state 필수)
        state = secrets.token_urlsafe(16)
        request.session["oauth_state"] = state
        params["state"] = state

        # kakao 특성: scope 등 필요하면 config에 넣어두고 합치기
        if config.get("scope"):
            params["scope"] = config["scope"]

        auth_url = f"{config['auth_url']}?{urlencode(params)}"
        return redirect(auth_url)

    @extend_schema(request=SocialLoginSerializer, responses={200: dict})
    def post(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return Response(
                {"error": "지원하지 않는 소셜 로그인"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data["token"]

        try:
            social_user_info = verify_social_token(provider, access_token)
            user = SocialAuthService.get_or_create_user_from_social(
                provider, social_user_info
            )

            if user.deleted_at or not user.is_active:
                logger.warning(f"Inactive user login attempt: {user.email}")
                return Response(
                    {"error": "비활성 계정"}, status=status.HTTP_403_FORBIDDEN
                )

            login(request, user)

            logger.info(f"Social login success: {provider} - {user.email}")

            return Response(
                {
                    "message": "로그인 성공",
                    "user": {
                        "email": user.email,
                        "nickname": user.nickname,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except SocialProviderNotFoundError as e:
            logger.error(f"Provider not found: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except SocialTokenInvalidError as e:
            logger.warning(f"Invalid social token: {provider}")
            return Response(
                {"error": "소셜 인증 실패"}, status=status.HTTP_401_UNAUTHORIZED
            )
        except ValueError as e:
            logger.warning(f"Social login validation error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Social login unexpected error: {str(e)}")
            return Response(
                {"error": "로그인 처리 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SocialCallbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={302: None})
    def get(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return Response({"error": "지원하지 않는 소셜 로그인"}, status=400)

        config = settings.SOCIAL_PROVIDERS[provider]
        code = request.GET.get("code")

        if not code:
            return Response({"error": "인증 코드 없음"}, status=400)

        if provider == "naver":
            state = request.GET.get("state")
            session_state = request.session.get("oauth_state")
            if not state or state != session_state:
                return Response({"error": "state 불일치"}, status=400)

        try:
            token_data = {
                "grant_type": "authorization_code",
                "client_id": config["client_id"],
                "client_secret": config.get("client_secret"),
                "code": code,
                "redirect_uri": config["redirect_uri"],
            }

            import requests

            token_response = requests.post(
                config["token_url"], data=token_data, timeout=5
            )

            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return Response({"error": "토큰 교환 실패"}, status=400)

            token_json = token_response.json()
            access_token = token_json.get("access_token")

            user_info_response = requests.get(
                config["user_info_url"],
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )

            if user_info_response.status_code != 200:
                return Response({"error": "사용자 정보 조회 실패"}, status=400)

            user_data = user_info_response.json()

            if provider == "kakao":
                social_user_info = {
                    "provider_user_id": str(user_data["id"]),
                    "email": user_data.get("kakao_account", {}).get("email"),
                    "nickname": user_data.get("properties", {}).get("nickname"),
                }
            elif provider == "naver":
                resp = user_data.get("response", {})
                social_user_info = {
                    "provider_user_id": resp.get("id"),
                    "email": resp.get("email"),
                    "nickname": resp.get("nickname") or resp.get("name"),
                }
            elif provider == "google":
                social_user_info = {
                    "provider_user_id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "nickname": user_data.get("name"),
                }

            user = SocialAuthService.get_or_create_user_from_social(
                provider, social_user_info
            )

            if user.deleted_at or not user.is_active:
                return Response({"error": "비활성 계정"}, status=403)

            login(request, user)
            logger.info(f"Social login success: {provider} - {user.email}")

            return redirect("http://localhost:3000/login/success")

        except Exception as e:
            logger.exception(f"Social callback error: {str(e)}")
            return redirect("http://localhost:3000/login/failed")


# 소셜 로그인 과정에서 자동 회원가입 / 로그인 기능
# 기존의 가입한 유저는 소셜 연동 누를시 소셜로 로그인 가능
class SocialAuthServiceView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def get_or_create_user_from_social(provider, social_user_info):
        email = social_user_info.get("email")
        nickname = social_user_info.get("nickname") or (
            email.split("@")[0] if email else None
        )

        if not email:
            raise ValueError("이메일 정보가 필요합니다.")

        try:
            user = User.objects.get(email__iexact=email)
            return user
        except User.DoesNotExist:
            # 닉네임 중복 처리
            base_nickname = nickname
            suffix = 1
            while User.objects.filter(nickname__iexact=nickname).exists():
                nickname = f"{base_nickname}{suffix}"
                suffix += 1

            user = User.objects.create_user(
                email=email,
                nickname=nickname,
                email_verified=True,
            )
            return user


class SocialLinkView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SocialLinkSerializer

    @extend_schema(request=SocialLinkSerializer, responses={200: dict})
    def post(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return Response(
                {"error": "지원하지 않는 소셜 로그인"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data["token"]

        try:
            social_user_info = verify_social_token(provider, access_token)

            SocialAuthService.link_social_account(
                request.user, provider, social_user_info
            )

            logger.info(f"Social account linked: {provider} - {request.user.email}")

            return Response(
                {"message": "소셜 계정 연결 완료"}, status=status.HTTP_200_OK
            )

        except SocialTokenInvalidError:
            logger.warning(f"Invalid social token for linking: {provider}")
            return Response(
                {"error": "소셜 인증 실패"}, status=status.HTTP_401_UNAUTHORIZED
            )

        except ValueError as e:
            logger.warning(f"Social link validation error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

        except Exception as e:
            logger.exception(f"Social link unexpected error: {str(e)}")
            return Response(
                {"error": "계정 연결 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SocialUnlinkView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SocialUnlinkSerializer

    @extend_schema(responses={200: dict})
    def delete(self, request, provider):
        if provider not in settings.SOCIAL_PROVIDERS:
            return Response(
                {"error": "지원하지 않는 소셜 로그인"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            SocialAuthService.unlink_social_account(request.user, provider)
            logger.info(f"Social account unlinked: {provider} - {request.user.email}")
            return Response(
                {"message": "소셜 계정 해제 완료"}, status=status.HTTP_200_OK
            )
        except SocialAccount.DoesNotExist:
            logger.warning(
                f"Social account not found: {provider} - {request.user.email}"
            )
            return Response(
                {"error": "연결된 소셜 계정 없음"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Social unlink unexpected error: {str(e)}")
            return Response(
                {"error": "계정 연결 해제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
