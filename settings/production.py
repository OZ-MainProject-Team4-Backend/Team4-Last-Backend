from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# 실제 서비스 도메인을 여기에 추가해야 합니다.
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['.p-e.kr'])

# HTTPS 설정
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 운영 환경용 소셜 로그인 리다이렉트 URI (환경 변수에서 가져오기)
SOCIAL_PROVIDERS["kakao"]["redirect_uri"] = env('KAKAO_REDIRECT_URI')
SOCIAL_PROVIDERS["naver"]["redirect_uri"] = env('NAVER_REDIRECT_URI')
SOCIAL_PROVIDERS["google"]["redirect_uri"] = env('GOOGLE_REDIRECT_URI')

# 운영 환경 이메일 설정 (환경 변수에서 가져오기)
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# CORS 설정 (실제 프론트엔드 도메인)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# CSRF 설정 (실제 서비스 도메인)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
