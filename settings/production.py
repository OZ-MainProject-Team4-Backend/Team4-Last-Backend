import os
from datetime import timedelta
from pathlib import Path

import environ

from .base import *

# ================== prod 전용 앱 ==================
INSTALLED_APPS += [
    "corsheaders",
]

# ================== prod 전용 미들웨어 조정 ==================
MIDDLEWARE = list(MIDDLEWARE)  # 안전 복사
if "corsheaders.middleware.CorsMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

# ============ BASE_DIR 설정 (Path로 통일) ============
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, "env/.env.prod"))


# ============ 기본 설정 ============
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-production-key")
DEBUG = False
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["team4.p-e.kr", "localhost", "127.0.0.1"],
)

# ============ 데이터베이스 설정 (RDS PostgreSQL) ============
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="team4-main"),
        "USER": env("POSTGRES_USER", default="minsoo"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="minsoo8070"),
        "HOST": env(
            "POSTGRES_HOST",
            default="team4-main.czoe0ewi2efo.ap-northeast-2.rds.amazonaws.com",
        ),
        "PORT": "5432",
    }
}

# ============ 캐시 설정 (Redis) ============
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
    }
}

# ============ S3 설정 ============
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-northeast-2")
AWS_S3_CUSTOM_DOMAIN = (
    f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
)

AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

AWS_DEFAULT_ACL = "public-read"

# ============ 이메일 설정 ============
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.naver.com")
EMAIL_PORT = env("EMAIL_PORT", default=465, cast=int)
EMAIL_USE_SSL = env("EMAIL_USE_SSL", default=True, cast=bool)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ============ 소셜 로그인 설정 ============
SOCIAL_PROVIDERS["naver"]["redirect_uri"] = env("NAVER_REDIRECT_URI", default="")
SOCIAL_PROVIDERS["google"]["redirect_uri"] = env("GOOGLE_REDIRECT_URI", default="")
SOCIAL_PROVIDERS["kakao"]["redirect_uri"] = env("KAKAO_REDIRECT_URI", default="")

# URL설정
FRONTEND_URL = env("FRONTEND_URL", default="https://team4.p-e.kr")

# ============ CORS 설정 ============
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "https://team4.p-e.kr",
        "http://localhost:5173",
        "https://oz-main.vercel.app",
        "https://www.team4.p-e.kr",
    ],
)
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CSRF_TRUSTED_ORIGINS = [
    "https://team4.p-e.kr",
    "http://localhost:5173",
    "https://oz-main.vercel.app",
    "https://www.team4.p-e.kr",
]

# ============ JWT 설정 ============
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

# ============ 쿠키 보안 설정 ============
SECURE_COOKIE_HTTPONLY = True
SECURE_COOKIE_SECURE = True
SECURE_COOKIE_SAMESITE = "Strict"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Strict"

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Strict"

REFRESH_COOKIE_SECURE = True
REFRESH_COOKIE_HTTPONLY = True
REFRESH_COOKIE_SAMESITE = "Strict"
SECURE_COOKIES = True

# ============ 보안 헤더 설정 ============
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'", "https://team4.p-e.kr"),
    "script-src": ("'self'", "'unsafe-inline'"),
    "img-src": ("'self'", "data:", f"https://{AWS_S3_CUSTOM_DOMAIN}"),
    "style-src": ("'self'", "'unsafe-inline'", f"https://{AWS_S3_CUSTOM_DOMAIN}"),
    "font-src": ("'self'", f"https://{AWS_S3_CUSTOM_DOMAIN}"),
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ============ 로깅 설정 ============
LOGGING_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOGGING_DIR):
    os.makedirs(LOGGING_DIR)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "app.log"),
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "error.log"),
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["file", "console", "error_file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["file", "console", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


APPEND_SLASH = False
