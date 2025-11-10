from .base import *

# ==================== 캐시 설정 ====================
CACHES = {
    "default": env.cache_url("CACHE_URL", default="locmem://"),
}


# ==================== 보안 설정 ====================
SECRET_KEY = env('DJANGO_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = env.list(
    'DJANGO_ALLOWED_HOSTS', default=['.p-e.kr', 'localhost', '127.0.0.1']
)

SESSION_COOKIE_SECURE = True


# ==================== 소셜 로그인 설정 ====================
SOCIAL_PROVIDERS["kakao"]["redirect_uri"] = env('KAKAO_REDIRECT_URI')
SOCIAL_PROVIDERS["naver"]["redirect_uri"] = env('NAVER_REDIRECT_URI')
SOCIAL_PROVIDERS["google"]["redirect_uri"] = env('GOOGLE_REDIRECT_URI')


# ==================== 이메일 설정 ====================
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# ==================== CORS 설정 ====================
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'https://your-production-frontend.com',
    ],
)


# ==================== JWT 설정 ====================
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
# 로컬 테스트: False, 배포: True로 변경
SECURE_SSL_REDIRECT = False

# DEBUG 상태에 따라 HSTS 설정
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
}


# ==================== Logging 설정 ====================
import os

LOGGING_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGGING_DIR):
    os.makedirs(LOGGING_DIR)

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
            'filename': os.path.join(LOGGING_DIR, 'app.log'),
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