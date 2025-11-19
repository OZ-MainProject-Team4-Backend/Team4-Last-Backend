import hashlib

from django.core.cache import cache
from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Token


class CustomJWTAuthentication(JWTAuthentication):
    """토큰 revoked 상태 및 DB 토큰과의 일치 여부를 확인하는 커스텀 JWT 인증 (최적화)"""

    CACHE_TIMEOUT = 3600  # 1시간

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result

        try:
            raw_token = str(validated_token)
        except Exception:
            raise AuthenticationFailed("토큰 처리 중 오류가 발생했습니다.")

        token_hash = hashlib.md5(raw_token.encode()).hexdigest()[:16]
        cache_key = f"token:{user.id}:{token_hash}"

        cached = cache.get(cache_key)
        if cached is not None:
            if cached.get("revoked"):
                raise AuthenticationFailed(
                    "로그아웃한 토큰이거나 유효하지 않은 토큰입니다"
                )
            return user, validated_token

        try:
            db_token = Token.objects.get(user=user, revoked=False)
        except Token.DoesNotExist:
            cache.set(cache_key, {"revoked": True}, timeout=self.CACHE_TIMEOUT)
            raise AuthenticationFailed("로그아웃한 토큰이거나 유효하지 않은 토큰입니다")

        if db_token.access_jwt != raw_token:
            cache.set(cache_key, {"revoked": True}, timeout=self.CACHE_TIMEOUT)
            raise AuthenticationFailed("유효하지 않은 토큰입니다 (토큰 불일치).")

        cache.set(cache_key, {"revoked": False}, timeout=self.CACHE_TIMEOUT)
        return user, validated_token


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.users.authentication.CustomJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
