from datetime import timedelta
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import Token


def create_jwt_pair_for_user(user, is_auto_login: bool = False):

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    now = timezone.now()

    # Access token: 30분
    access_exp = now + timedelta(minutes=30)

    refresh_exp = (
        now + timedelta(days=7)
        if is_auto_login
        else now + timedelta(seconds=1)  # ← 거의 즉시 만료
    )

    Token.objects.update_or_create(
        user=user,
        defaults={
            "access_jwt": str(access),
            "refresh_jwt": str(refresh),
            "access_expires_at": access_exp,
            "refresh_expires_at": refresh_exp,
            "revoked": False,
            "is_auto_login": is_auto_login,
        },
    )

    return {
        "access": str(access),
        "refresh": str(refresh),
        "access_expires_at": access_exp,
        "refresh_expires_at": refresh_exp,
        "is_auto_login": is_auto_login,
    }


def revoke_token(user):

    try:
        token = Token.objects.get(user=user)
        token.revoked = True
        token.save(update_fields=["revoked"])
    except Token.DoesNotExist:
        pass


def get_token_status(user):

    try:
        token = Token.objects.get(user=user)
        return {
            "revoked": token.revoked,
            "is_auto_login": token.is_auto_login,
            "access_expires_at": token.access_expires_at,
            "refresh_expires_at": token.refresh_expires_at,
        }
    except Token.DoesNotExist:
        return None