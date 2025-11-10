from .base import *

# ==================== 캐시 설정 ====================
CACHES = {
    "default": env.cache_url("CACHE_URL", default="locmem://"),
}


# ==================== 보안 설정 ====================
# 시크릿키
SECRET_KEY = env('DJANGO_SECRET_KEY')

# 운영환경이니까 디버그 끔
DEBUG = False

# 실제 서비스 도메인 + 로컬 테스트용 도메인 포함
ALLOWED_HOSTS = env.list(
    'DJANGO_ALLOWED_HOSTS', default=['.p-e.kr', 'localhost', '127.0.0.1']
)

# HTTPS 설정
SESSION_COOKIE_SECURE = True


# ==================== 소셜 로그인 설정 ====================
# 운영 환경용 소셜 로그인 리다이렉트 URI
SOCIAL_PROVIDERS["kakao"]["redirect_uri"] = env('KAKAO_REDIRECT_URI')
SOCIAL_PROVIDERS["naver"]["redirect_uri"] = env('NAVER_REDIRECT_URI')
SOCIAL_PROVIDERS["google"]["redirect_uri"] = env('GOOGLE_REDIRECT_URI')


# ==================== 이메일 설정 ====================
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ==================== CORS 설정 ====================
# 프론트엔드 도메인만 허용
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'https://your-production-frontend.com',
    ],
)


# ==================== JWT 설정 ====================
# 운영 환경에서는 HTTPS 필수
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}


# ==================== 보안 헤더 설정 ====================
# HSTS (HTTP Strict-Transport-Security)
SECURE_HSTS_SECONDS = 31536000  # 1년
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 기타 보안 설정
SECURE_SSL_REDIRECT = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
}


# ==================== Logging 설정 ====================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
}