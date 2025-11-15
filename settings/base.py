# settings/base.py

import os
from datetime import timedelta
from pathlib import Path
from typing import TypedDict

import environ
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# ============ 환경변수 로드 (한 번만) ============
ENV_FILE = os.environ.get("ENV_FILE", "env/.env")
load_dotenv(dotenv_path=ENV_FILE)

env = environ.Env()
ENV_PATH = os.path.join(BASE_DIR, "env/.env")
if os.path.exists(ENV_PATH):
    environ.Env.read_env(ENV_PATH)

# ============ API 키 설정 ============
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============ 기본값 설정 (mypy 및 개발용) ============
SECRET_KEY = env(
    "DJANGO_SECRET_KEY", default='django-insecure-key-for-development-and-mypy'
)

# DEBUG, ALLOWED_HOSTS are defined in development.py or production.py
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = ['*']

SECURE_COOKIES = True

# ==================== DATABASE ====================
# 기본값을 제공하여 mypy 및 테스트 환경에서도 작동
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="postgres"),
        "USER": env("POSTGRES_USER", default="postgres"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="password"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'apps.users',
    'apps.locations',
    'apps.recommend',
    "apps.weather",
    'apps.core',
    'apps.diary',
    'apps.chat',
    'storages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ==================== CORS 설정 ====================
CORS_ALLOWED_ORIGINS: list[str] = []
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'settings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'settings.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==================== Redis Cache 설정 ====================
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}

# ==================== 이메일 설정 ====================
EMAIL_VERIF_CODE_TTL = 300  # 5분
EMAIL_PREVER_TTL = 1800  # 30분
EMAIL_VERIF_RESEND_TTL = 60  # 1분
EMAIL_VERIF_MAX_PER_HOUR = 5

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.naver.com"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ==================== Internationalization ====================
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# ==================== 인증 설정 ====================
AUTH_USER_MODEL = "users.User"

# JWT 설정
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ==================== REST Framework 설정 ====================
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.users.authentication.CustomJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

# ==================== Swagger/Spectacular 설정 ====================
SPECTACULAR_SETTINGS = {
    "TITLE": "Your Project API",
    "DESCRIPTION": "Your project description",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SECURITY": [{"bearerAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"',
            }
        }
    },
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
}

# ==================== 정적 파일 ====================
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== 소셜 로그인 설정 ====================
SOCIAL_PROVIDERS = {
    "kakao": {
        "name": "카카오",
        "client_id": os.environ.get("KAKAO_CLIENT_ID", ""),
        "client_secret": os.environ.get("KAKAO_CLIENT_SECRET", ""),
        "auth_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "user_info_url": "https://kapi.kakao.com/v2/user/me",
        "redirect_uri": os.environ.get("KAKAO_REDIRECT_URI", ""),
        "api_url": "https://kapi.kakao.com/v2/user/me",
        "timeout": 5,
    },
    "naver": {
        "name": "네이버",
        "client_id": os.environ.get("NAVER_CLIENT_ID", ""),
        "client_secret": os.environ.get("NAVER_CLIENT_SECRET", ""),
        "auth_url": "https://nid.naver.com/oauth2.0/authorize",
        "token_url": "https://nid.naver.com/oauth2.0/token",
        "user_info_url": "https://openapi.naver.com/v1/nid/me",
        "redirect_uri": os.environ.get("NAVER_REDIRECT_URI", ""),
        "api_url": "https://openapi.naver.com/v1/nid/me",
        "timeout": 5,
    },
    "google": {
        "name": "구글",
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
        "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI", ""),
        "api_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "timeout": 5,
    },
}


# ==================== OpenWeather 설정 ====================
class OpenWeatherConf(TypedDict):
    BASE_URL: str
    API_KEY: str
    TIMEOUT: int


OPENWEATHER: OpenWeatherConf = {
    "BASE_URL": "https://api.openweathermap.org",
    "API_KEY": os.getenv("OPENWEATHER_API_KEY", ""),
    "TIMEOUT": 5,
}
