import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import Token

User = get_user_model()
logger = logging.getLogger(__name__)


from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken


def create_jwt_pair_for_user(user, is_auto_login: bool = False):
    """JWT 토큰 쌍(Access, Refresh) 생성"""
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    token_obj = RefreshToken.for_user(user)
    access_token_obj = token_obj.access_token

    # JWT의 exp를 datetime으로 변환
    from datetime import datetime

    access_exp_timestamp = access_token_obj.get("exp")
    access_expires_at = datetime.fromtimestamp(access_exp_timestamp, tz=timezone.utc)

    if is_auto_login:
        refresh_exp_timestamp = token_obj.get("exp")
        refresh_expires_at = datetime.fromtimestamp(
            refresh_exp_timestamp, tz=timezone.utc
        )
    else:
        refresh_expires_at = timezone.now() + timedelta(days=1)

    token, created = Token.objects.get_or_create(user=user)
    token.access_jwt = access_token
    token.access_expires_at = access_expires_at
    token.refresh_jwt = refresh_token
    token.refresh_expires_at = refresh_expires_at
    token.is_auto_login = is_auto_login
    token.revoked = False
    token.save()

    logger.info(f"JWT pair created for user {user.id} - auto_login: {is_auto_login}")

    return {
        "access": access_token,
        "access_expires_at": access_expires_at,
        "refresh": refresh_token,
        "refresh_expires_at": refresh_expires_at,
    }


def revoke_token(user):
    """사용자의 토큰 폐기 (로그아웃 시)"""
    try:
        token = Token.objects.get(user=user)
        token.revoked = True
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked", "revoked_at"])
        logger.info(f"Token revoked for user {user.id}")
    except Token.DoesNotExist:
        logger.warning(f"Token not found for user {user.id} during revocation")
        raise


def rotate_refresh_token(user, is_auto_login: bool):
    """Refresh 토큰 회전 (보안 강화)"""
    try:
        new_refresh = RefreshToken.for_user(user)
        new_refresh_token = str(new_refresh)

        if is_auto_login:
            refresh_expires_at = timezone.now() + timedelta(days=7)
        else:
            refresh_expires_at = timezone.now() + timedelta(days=1)

        token = Token.objects.get(user=user)
        token.refresh_jwt = new_refresh_token
        token.refresh_expires_at = refresh_expires_at
        token.is_auto_login = is_auto_login
        token.save(update_fields=["refresh_jwt", "refresh_expires_at", "is_auto_login"])

        logger.info(
            f"Refresh token rotated for user {user.id} - auto_login: {is_auto_login}"
        )

        return {
            "refresh": new_refresh_token,
            "refresh_expires_at": refresh_expires_at,
        }

    except Token.DoesNotExist:
        logger.error(f"Token not found for user {user.id}")
        raise


def is_token_valid(user):
    """사용자의 토큰이 유효한지 확인"""
    try:
        token = Token.objects.get(user=user, revoked=False)
        return token.refresh_expires_at > timezone.now()
    except Token.DoesNotExist:
        return False


def get_token_info(user):
    """사용자의 토큰 정보 조회"""
    try:
        token = Token.objects.get(user=user)
        return {
            "access_expires_at": token.access_expires_at,
            "refresh_expires_at": token.refresh_expires_at,
            "is_auto_login": token.is_auto_login,
            "is_revoked": token.revoked,
        }
    except Token.DoesNotExist:
        logger.warning(f"Token not found for user {user.id}")
        raise
