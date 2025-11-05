from __future__ import annotations
from typing import TYPE_CHECKING, Dict

from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import SocialAccount
from ..utils.social_auth import verify_social_token

# runtime에서 사용할 ORM 클래스
User = get_user_model()

# 타입 검사(mypy) 전용 실제 모델 타입
if TYPE_CHECKING:
    from ..models import User as UserModel  # type: ignore

class SocialAuthService:
    @staticmethod
    @transaction.atomic
    def get_or_create_user_from_social(provider: str, social_user_info: Dict) -> "UserModel":
        provider_user_id = social_user_info["provider_user_id"]
        email = social_user_info.get("email")
        nickname = social_user_info.get("nickname")

        try:
            social_account = SocialAccount.objects.select_related("user").get(
                provider=provider,
                provider_user_id=provider_user_id
            )
            return social_account.user

        except SocialAccount.DoesNotExist:
            if not email:
                raise ValueError(
                    "이메일 정보가 필요합니다. 소셜 로그인 설정에서 이메일 제공 동의 해주세요."
                )

            user = User.objects.filter(
                email__iexact=email,
                deleted_at__isnull=True
            ).first()

            if not user:
                # create_user 시그니처가 프로젝트마다 다를 수 있으니 필요에 따라 인자 조절
                user = User.objects.create_user(
                    email=email,
                    nickname=nickname or email.split("@")[0],
                    email_verified=True,
                )

            SocialAccount.objects.create(
                user=user,
                provider=provider,
                provider_user_id=provider_user_id,
            )

            return user

    @staticmethod
    @transaction.atomic
    def link_social_account(user: "UserModel", provider: str, social_user_info: Dict) -> SocialAccount:
        provider_user_id = social_user_info["provider_user_id"]

        existing = SocialAccount.objects.filter(
            provider=provider,
            provider_user_id=provider_user_id
        ).exclude(user=user).exists()

        if existing:
            raise ValueError("이미 다른 계정에 연결된 소셜 계정입니다.")

        if SocialAccount.objects.filter(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id
        ).exists():
            raise ValueError("이미 연결된 소셜 계정입니다.")

        return SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
        )

    @staticmethod
    def unlink_social_account(user: "UserModel", provider: str) -> None:
        social_account = SocialAccount.objects.get(
            user=user,
            provider=provider,
        )
        social_account.delete()