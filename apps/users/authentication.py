from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Token


class CustomJWTAuthentication(JWTAuthentication):
    """토큰 revoked 상태를 확인하는 커스텀 JWT 인증"""

    def authenticate(self, request):
        result = super().authenticate(request)

        if result is None:
            return None

        user, validated_token = result

        # 토큰이 revoked 상태인지 확인
        try:
            token = Token.objects.get(user=user, revoked=False)
        except Token.DoesNotExist:
            raise AuthenticationFailed("로그아웃한 토큰이거나 유효하지 않은 토큰입니다")

        return user, validated_token