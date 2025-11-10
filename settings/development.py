from .base import *

# Provide a default secret key for development and tools like mypy
SECRET_KEY = env(
    'DJANGO_SECRET_KEY', default='a-dummy-secret-key-for-development-and-mypy'
)

# Provide a default database URL for development and tools like mypy
DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://user:password@localhost:5432/mydatabase"
    )
}

# Provide a default cache URL for development and tools like mypy
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]  # 개발 환경에서는 모든 호스트를 허용


# ==================== 소셜 로그인 설정 ====================
# 개발 환경용 소셜 로그인 리다이렉트 URI
SOCIAL_PROVIDERS["kakao"][
    "redirect_uri"
] = "http://localhost:8000/api/auth/social/kakao/callback"
SOCIAL_PROVIDERS["naver"][
    "redirect_uri"
] = "http://localhost:8000/api/auth/social/naver/callback"
SOCIAL_PROVIDERS["google"][
    "redirect_uri"
] = "http://localhost:8000/api/auth/social/google/callback"


# ==================== 이메일 설정 ====================
# 개발 중에는 이메일을 콘솔에 출력
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ==================== CORS 설정 ====================
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]


# ==================== JWT 설정 ====================
# 개발 환경에서는 토큰 만료 시간을 길게 설정 (선택사항)
# SIMPLE_JWT = {
#     'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
#     'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
#     'ROTATE_REFRESH_TOKENS': True,
#     'BLACKLIST_AFTER_ROTATION': True,
#     'UPDATE_LAST_LOGIN': True,
#     'ALGORITHM': 'HS256',
#     'SIGNING_KEY': SECRET_KEY,
# }


# ==================== 로깅 설정 ====================
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
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
