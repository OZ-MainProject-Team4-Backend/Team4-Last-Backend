from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Token


class CustomJWTAuthentication(JWTAuthentication):
    """토큰 revoked 상태를 확인하는 커스텀 JWT 인증"""

    def authenticate(self, request):
        result = super().authenticate(request)

        if result is None:
            return None

        user, validated_token = result

        # 토큰이 revoked 상태인지 캐시로 확인 (DB 쿼리 최소화)
        from django.core.cache import cache

        cache_key = f"token_revoked:{user.id}"
        is_revoked = cache.get(cache_key)

        if is_revoked is None:
            try:
                token = Token.objects.get(user=user, revoked=False)
                cache.set(cache_key, False, timeout=3600)  # 1시간 캐시
            except Token.DoesNotExist:
                cache.set(cache_key, True, timeout=3600)
                raise AuthenticationFailed(
                    "로그아웃한 토큰이거나 유효하지 않은 토큰입니다"
                )
        elif is_revoked:
            raise AuthenticationFailed("로그아웃한 토큰이거나 유효하지 않은 토큰입니다")

        return user, validated_token
