import logging
from datetime import timedelta
from typing import Any, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import SocialAccount, Token
from ..serializers import LoginResponseSerializer
from ..utils.auth_utils import (
    EMAIL_PREVER_TTL,
    EMAIL_VERIF_CODE_TTL,
    EMAIL_VERIF_MAX_PER_HOUR,
    EMAIL_VERIF_RESEND_TTL,
    gen_code,
    get_user_data,
    key_count,
    key_nickname_valid,
    key_preverified,
    key_resend,
    key_verif,
)
from ..utils.send_email import send_verification_email
from ..utils.social_auth import SocialTokenInvalidError, verify_social_token
from .social_auth_service import SocialAuthService
from .token_service import create_jwt_pair_for_user, revoke_token

User = get_user_model()
logger = logging.getLogger(__name__)


# ============ Nickname Service ============
def validate_nickname_service(
    nickname: str,
) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """닉네임 유효성 검사"""
    if User.objects.filter(nickname__iexact=nickname, deleted_at__isnull=True).exists():
        return (
            False,
            "nickname_already_in_use",
            "이미 사용 중인 닉네임입니다",
            status.HTTP_400_BAD_REQUEST,
        )

    cache.set(key_nickname_valid(nickname), True, timeout=300)
    return (True, None, None, None)


# ============ Email Verification Service ============
def send_email_verification_service(
    email: str,
) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """인증 이메일 발송"""
    # ✅ 추가: 활성 계정이 있으면 자동 탈퇴 처리
    existing_active = User.objects.filter(
        email__iexact=email, email_verified=True, deleted_at__isnull=True
    ).first()
    if existing_active:
        existing_active.deleted_at = timezone.now()
        existing_active.is_active = False
        existing_active.save(update_fields=["deleted_at", "is_active"])
        logger.info(f"Active user auto-deleted: {email}")

    if cache.get(key_resend(email)):
        return (
            False,
            "email_resend_limit",
            "재전송 제한",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    cnt_key = key_count(email)
    cnt = cache.get(cnt_key) or 0
    if cnt >= EMAIL_VERIF_MAX_PER_HOUR:
        return (
            False,
            "email_send_limit",
            "발송 초과",
            status.HTTP_429_TOO_MANY_REQUESTS,
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
        return (
            False,
            "email_send_failed",
            "메일 발송 실패",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return (True, None, None, None)


def verify_email_code_service(
    email: str, code: str
) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """이메일 인증 코드 검증"""
    cached = cache.get(key_verif(email))
    code_stripped = code.strip() if code else ""
    if not cached or cached != code_stripped:
        return (
            False,
            "code_invalid_or_expired",
            "코드 만료 또는 불일치",
            status.HTTP_400_BAD_REQUEST,
        )

    cache.delete(key_verif(email))
    cache.set(key_preverified(email), True, timeout=EMAIL_PREVER_TTL)
    return (True, None, None, None)


# ============ Signup Service ============
def signup_user_service(
    validated_data: dict,
) -> Tuple[bool, Optional[dict], Optional[str], Optional[str], Optional[int]]:
    """사용자 회원가입"""
    email = validated_data.get("email")
    if not email:
        return (
            False,
            None,
            "email_invalid",
            "이메일이 필요합니다",
            status.HTTP_400_BAD_REQUEST,
        )

    email = email.strip().lower()

    if not cache.get(key_preverified(email)):
        return (
            False,
            None,
            "email_not_verified",
            "이메일 미검증",
            status.HTTP_400_BAD_REQUEST,
        )

    # ⭐ 탈퇴한 계정 먼저 완전 삭제
    deleted_user = User.objects.filter(
        email__iexact=email, deleted_at__isnull=False
    ).first()
    if deleted_user:
        deleted_user.delete()  # 🔧 완전 삭제
        logger.info(f"Deleted account purged: {email}")

    if User.objects.filter(email__iexact=email, deleted_at__isnull=True).exists():
        return (
            False,
            None,
            "email_duplicate",
            "이메일 중복",
            status.HTTP_400_BAD_REQUEST,
        )

    nickname = validated_data.get("nickname")
    if (
        nickname
        and User.objects.filter(
            nickname__iexact=nickname, deleted_at__isnull=True
        ).exists()
    ):
        return (
            False,
            None,
            "nickname_duplicate",
            "닉네임 중복",
            status.HTTP_400_BAD_REQUEST,
        )

    user_data = {
        'email': email,  # 🔧 정제된 email 사용
        'password': validated_data.get('password'),
        'nickname': validated_data.get('nickname'),
        'name': validated_data.get('name'),
        'age_group': validated_data.get('age_group'),
        'gender': validated_data.get('gender'),
    }
    user_data = {k: v for k, v in user_data.items() if v is not None}

    user = User.objects.create_user(**user_data)
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    cache.delete(key_preverified(email))

    return (True, get_user_data(user), None, None, status.HTTP_201_CREATED)


# ============ Login Service ============
def handle_login(user: Any, is_auto_login: bool) -> dict:
    """로그인 처리"""
    tokens = create_jwt_pair_for_user(user, is_auto_login)

    response_data = {
        "user": get_user_data(user),
        "access": tokens["access"],
        "access_expires_at": tokens["access_expires_at"],
        "is_auto_login": is_auto_login,
    }
    response_serializer = LoginResponseSerializer(response_data)

    return {
        "serialized_data": response_serializer.data,
        "refresh_token": tokens["refresh"],
    }


# ============ Logout Service ============
def logout_user_service(user: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """로그아웃 처리"""
    try:
        revoke_token(user)
    except Token.DoesNotExist:
        pass
    return (True, None, None)


# ============ Refresh Token Service ============
def refresh_token_service(
    refresh_token_value: Optional[str],
) -> Tuple[
    bool,
    Optional[str],
    Optional[Any],
    Optional[str],
    Optional[bool],
    Optional[str],
    Optional[str],
    Optional[int],
]:
    """Refresh 토큰 갱신"""
    if not refresh_token_value:
        return (
            False,
            None,
            None,
            None,
            None,
            "refresh_token_required",
            "Refresh 토큰이 필요합니다",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        refresh = RefreshToken(refresh_token_value)  # type: ignore
        new_access_token = str(refresh.access_token)
        user_id = refresh.get("user_id")
        user = User.objects.get(id=user_id)

        token = Token.objects.get(user=user, revoked=False)

        token.access_jwt = new_access_token
        token.access_expires_at = timezone.now() + timedelta(minutes=15)

        new_refresh = RefreshToken.for_user(user)
        token.refresh_jwt = str(new_refresh)
        token.refresh_expires_at = timezone.now() + timedelta(days=7)

        token.save(
            update_fields=[
                "access_jwt",
                "access_expires_at",
                "refresh_jwt",
                "refresh_expires_at",
            ]
        )

        return (
            True,
            new_access_token,
            token.access_expires_at,
            str(new_refresh),
            token.is_auto_login,
            None,
            None,
            None,
        )

    except Token.DoesNotExist:
        return (
            False,
            None,
            None,
            None,
            None,
            "token_not_found",
            "토큰 정보를 찾을 수 없습니다",
            status.HTTP_401_UNAUTHORIZED,
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return (
            False,
            None,
            None,
            None,
            None,
            "invalid_refresh_token",
            "유효하지 않은 Refresh 토큰",
            status.HTTP_401_UNAUTHORIZED,
        )


# ============ Profile Update Service ============
def email_change_service(
    user: Any, new_email: Optional[str]
) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """이메일 변경 인증 코드 발송"""
    if not new_email:
        return (
            False,
            "email_invalid",
            "유효하지 않은 이메일",
            status.HTTP_400_BAD_REQUEST,
        )

    new_email_stripped = new_email.strip().lower()
    if new_email_stripped == user.email.lower():
        return (True, None, None, None)

    pending_key = f"email_change_pending:{user.id}:{new_email_stripped}"
    code = gen_code(6)
    cache.set(pending_key, code, timeout=EMAIL_PREVER_TTL)

    try:
        send_verification_email(new_email_stripped, code)
    except Exception as e:
        cache.delete(pending_key)
        logger.exception(f"Email send failed: {str(e)}")
        return (
            False,
            "email_send_failed",
            "메일 발송 실패",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return (True, None, None, None)


def verify_email_change_service(
    user: Any, new_email: str, code: str
) -> Tuple[bool, Optional[dict], Optional[str], Optional[str], Optional[int]]:
    """이메일 변경 검증"""
    new_email_stripped = new_email.strip().lower() if new_email else ""
    code_stripped = code.strip() if code else ""

    if not new_email_stripped or not code_stripped:
        return (
            False,
            None,
            "validation_failed",
            "email과 인증코드가 필요합니다",
            status.HTTP_400_BAD_REQUEST,
        )

    pending_key = f"email_change_pending:{user.id}:{new_email_stripped}"
    cached = cache.get(pending_key)
    if not cached or cached != code_stripped:
        return (
            False,
            None,
            "code_invalid_or_expired",
            "코드 만료 또는 불일치",
            status.HTTP_400_BAD_REQUEST,
        )

    user.email = new_email_stripped
    user.email_verified = True
    user.save(update_fields=["email", "email_verified"])
    cache.delete(pending_key)

    return (True, get_user_data(user), None, None, status.HTTP_200_OK)


# ============ Favorite Regions Service ============
def update_favorite_regions_service(
    user: Any, regions: list
) -> Tuple[bool, list, Optional[str], Optional[str], Optional[int]]:
    """즐겨찾는 지역 업데이트"""
    user.favorite_regions = regions
    user.updated_at = timezone.now()
    user.save(update_fields=["favorite_regions", "updated_at"])

    return (True, regions, None, None, status.HTTP_200_OK)


# ============ User Deletion Service ============
def delete_user_service(
    user: Any,
) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """사용자 탈퇴"""
    if user.deleted_at:
        return (
            False,
            "already_deleted",
            "이미 탈퇴한 계정입니다",
            status.HTTP_400_BAD_REQUEST,
        )

    user.deleted_at = timezone.now()
    user.is_active = False
    user.save(update_fields=["deleted_at", "is_active"])
    logger.info(f"User deleted: {user.email}")

    return (True, None, None, None)


# ============ Social Login Service ============
def social_login_service(
    provider: str, token: str, is_auto_login: bool
) -> Tuple[
    bool, Optional[dict], Optional[str], Optional[str], Optional[str], Optional[int]
]:
    """소셜 로그인

    Returns:
        success, response_data, refresh_token, error_code, error_message, http_status
    """
    try:
        social_user_info = verify_social_token(provider, token)
        user = SocialAuthService.get_or_create_user_from_social(
            provider, social_user_info
        )

        if user.deleted_at or not user.is_active:
            return (
                False,
                None,
                None,
                "account_inactive",
                "비활성 계정",
                status.HTTP_403_FORBIDDEN,
            )

        tokens = create_jwt_pair_for_user(user, is_auto_login)
        logger.info(f"Social login success: {provider} - {user.email}")

        response_data = {
            "user": get_user_data(user),
            "access": tokens["access"],
            "access_expires_at": tokens["access_expires_at"],
            "is_auto_login": is_auto_login,
        }

        return (True, response_data, tokens["refresh"], None, None, status.HTTP_200_OK)

    except SocialTokenInvalidError:
        return (
            False,
            None,
            None,
            "token_invalid",
            "소셜 인증 실패",
            status.HTTP_401_UNAUTHORIZED,
        )
    except Exception as e:
        logger.exception(f"Social login error: {str(e)}")
        return (
            False,
            None,
            None,
            "internal_error",
            "로그인 처리 중 오류가 발생했습니다",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============ Social Callback Service ============
def social_callback_service(
    provider: str, code: Optional[str], config: dict
) -> Tuple[bool, Optional[dict], Optional[str], Optional[str]]:
    """소셜 콜백 처리"""
    import requests

    if not code:
        return (False, None, "code_missing", "인증 코드가 없습니다")

    try:
        token_data = {
            "grant_type": "authorization_code",
            "client_id": config["client_id"],
            "client_secret": config.get("client_secret"),
            "code": code,
            "redirect_uri": config["redirect_uri"],
        }

        token_response = requests.post(config["token_url"], data=token_data, timeout=5)
        if token_response.status_code != 200:
            return (False, None, "token_fetch_failed", "토큰 획득 실패")

        access_token = token_response.json().get("access_token")
        user_info_response = requests.get(
            config["user_info_url"],
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )

        if user_info_response.status_code != 200:
            return (False, None, "user_info_fetch_failed", "사용자 정보 획득 실패")

        user_data = user_info_response.json()
        social_user_info = _parse_social_user(provider, user_data)
        user = SocialAuthService.get_or_create_user_from_social(
            provider, social_user_info
        )

        if user.deleted_at or not user.is_active:
            return (False, None, "account_inactive", "비활성 계정")

        tokens = create_jwt_pair_for_user(user, is_auto_login=False)
        logger.info(f"Social callback success: {provider} - {user.email}")

        response_data = {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": get_user_data(user),
        }

        return (True, response_data, None, None)

    except Exception as e:
        logger.exception(f"Social callback error: {str(e)}")
        return (False, None, "callback_error", "콜백 처리 중 오류 발생")


def _parse_social_user(provider: str, user_data: dict) -> dict:
    """소셜 제공자별 사용자 정보 파싱"""
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


# ============ Social Link Service ============
def social_link_service(
    user: Any, provider: str, token: str
) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """소셜 계정 연결"""
    try:
        social_user_info = verify_social_token(provider, token)
        SocialAuthService.link_social_account(user, provider, social_user_info)
        logger.info(f"Social account linked: {provider} - {user.email}")
        return (True, None, None, None)
    except SocialTokenInvalidError:
        return (False, "token_invalid", "소셜 인증 실패", status.HTTP_401_UNAUTHORIZED)
    except ValueError as e:
        return (False, "validation_failed", str(e), status.HTTP_409_CONFLICT)
    except Exception as e:
        logger.exception(f"Social link error: {str(e)}")
        return (
            False,
            "internal_error",
            "계정 연결 중 오류가 발생했습니다",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============ Social Unlink Service ============
def social_unlink_service(
    user: Any, provider: str
) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """소셜 계정 연결 해제"""
    try:
        SocialAuthService.unlink_social_account(user, provider)
        logger.info(f"Social account unlinked: {provider} - {user.email}")
        return (True, None, None, None)
    except SocialAccount.DoesNotExist:
        return (
            False,
            "social_account_not_found",
            "연결된 소셜 계정 없음",
            status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.exception(f"Social unlink error: {str(e)}")
        return (
            False,
            "internal_error",
            "계정 연결 해제 중 오류가 발생했습니다",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
