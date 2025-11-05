
import requests
import logging
from typing import Dict
from django.conf import settings

logger = logging.getLogger(__name__)

class SocialAuthError(Exception):
    """소셜 인증 에러"""
    pass

class SocialProviderNotFoundError(SocialAuthError):
    """지원하지 않는 소셜 프로바이더"""
    pass

class SocialTokenInvalidError(SocialAuthError):
    """유효하지 않은 소셜 토큰"""
    pass

def get_provider_config(provider: str) -> Dict:
    config = settings.SOCIAL_PROVIDERS.get(provider)
    if not config:
        raise SocialProviderNotFoundError(f"지원하지 않는 소셜 로그인: {provider}")
    return config

def verify_kakao_token(access_token:str) -> Dict:
    config = get_provider_config("kakao")

    try:
        response = requests.get(
            config["api_url"],
            headers={"Authorization":f"Bearer {access_token}"},
            timeout=config["timeout"]
        )

        if response.status_code != 200:
            logger.warning(f"kakao token verification failed: {response.status_code}")
            raise SocialTokenInvalidError ("카카오 토큰 검증 실패")

        data = response.json()
        kakao_account = data.get("kakao_account",{})

        return {
            "provider_user_id": str(data["id"]),
            "email": kakao_account.get("email"),
            "nickname": data.get("properties",{}).get("nickname"),
        }

    except requests.RequestException as e:
        logger.error(f"kakao API request failed: {str(e)}")
        raise SocialTokenInvalidError("카카오 API 호출 실패")

def verify_naver_token(access_token:str) -> Dict:
    config = get_provider_config("naver")

    try:
        response = requests.get(
            config["api_url"],
            headers={"Authorization":f"Bearer {access_token}"},
            timeout=config["timeout"]
        )

        if response.status_code != 200:
            logger.warning(f"naver token verification failed: {response.status_code}")
            raise SocialTokenInvalidError ("네이버 토큰 검증 실패")

        data = response.json()

        if data.get("resultcode") != "00":
            raise SocialTokenInvalidError("네이버 토큰 검증 실패")

        resp = data.get("response", {})
        return {
            "provider_user_id": resp.get("id"),
            "email": resp.get("email"),
            "nickname": resp.get("nickname") or resp.get("name"),
        }

    except requests.RequestException as e:
        logger.error(f"naver API request failed: {str(e)}")
        raise SocialTokenInvalidError("네이버 API 호출 실패")

def verify_google_token(access_token: str) -> Dict:
    config = get_provider_config("google")

    try:
        response = requests.get(
            config["api_url"],
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=config["timeout"]
        )

        if response.status_code != 200:
            logger.warning(f"google token verification failed: {response.status_code}")
            raise SocialTokenInvalidError("구글 토큰 검증 실패")

        data = response.json()
        return {
            "provier_user_id":data.get("id"),
            "email": data.get("email"),
            "nickname":data.get("name"),
        }

    except requests.RequestException as e:
        logger.error(f"Google API request failed: {str(e)}")
        raise SocialTokenInvalidError("구글 API 호출 실패")

SOCIAL_VERIFIERS = {
    "kakao": verify_kakao_token,
    "naver": verify_naver_token,
    "google": verify_google_token,
}

def verify_social_token(provider: str, access_token: str) -> Dict:
    verifier = SOCIAL_VERIFIERS.get(provider)
    if not verifier:
        raise SocialProviderNotFoundError(f"지원하지 않는 소셜 로그인: {provider}")

    return verifier(access_token)