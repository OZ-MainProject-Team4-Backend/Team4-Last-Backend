from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]  # 개발 환경에서는 모든 호스트를 허용

# 개발 환경용 소셜 로그인 리다이렉트 URI
SOCIAL_PROVIDERS["kakao"]["redirect_uri"] = "http://localhost:8000/api/auth/social/kakao/callback"
SOCIAL_PROVIDERS["naver"]["redirect_uri"] = "http://localhost:8000/api/auth/social/naver/callback"
SOCIAL_PROVIDERS["google"]["redirect_uri"] = "http://localhost:8000/api/auth/social/google/callback"

# 개발 중에는 이메일을 콘솔에 출력
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS 설정
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
]
