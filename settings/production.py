from .base import *
from django.core.cache import caches

# 캐시 설정
CACHES = {
    "default": env.cache_url("CACHE_URL", default="locmem://"),
}

# 시크릿키
SECRET_KEY = env('DJANGO_SECRET_KEY')

# 운영환경이니까 디버그 끔
DEBUG = False

# 실제 서비스 도메인 + Swagger/로컬 테스트용 도메인 포함
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['.p-e.kr', 'localhost', '127.0.0.1'])

# HTTPS 설정
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 운영 환경용 소셜 로그인 리다이렉트 URI
SOCIAL_PROVIDERS["kakao"]["redirect_uri"] = env('KAKAO_REDIRECT_URI')
SOCIAL_PROVIDERS["naver"]["redirect_uri"] = env('NAVER_REDIRECT_URI')
SOCIAL_PROVIDERS["google"]["redirect_uri"] = env('GOOGLE_REDIRECT_URI')

# 이메일 설정
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# CORS 설정 - 프론트 + Swagger 테스트용 도메인
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'https://your-production-frontend.com',
        'http://localhost:3000',
    ]
)

# CSRF 신뢰 도메인 - Swagger/로컬 테스트 허용
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[
        'https://your-production-frontend.com',
        'http://localhost:8000',
    ]
)
