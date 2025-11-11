from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import SocialAccount

User = get_user_model()

if TYPE_CHECKING:
    from ..models import User as UserModel


class SocialAuthService:
    @staticmethod
    @transaction.atomic
    def get_or_create_user_from_social(
            provider: str, social_user_info: Dict
    ) -> "UserModel":
        provider_user_id = social_user_info["provider_user_id"]
        email = social_user_info.get("email")
        nickname = social_user_info.get("nickname")

        # 1. 기존 소셜 계정 확인
        try:
            social_account = SocialAccount.objects.select_related("user").get(
                provider=provider, provider_user_id=provider_user_id
            )
            return social_account.user

        except SocialAccount.DoesNotExist:
            pass

        # 2. 이메일 필수 확인
        if not email:
            raise ValueError(
                "이메일 정보가 필요합니다. 소셜 로그인 설정에서 이메일 제공 동의 해주세요."
            )

        # 3. 기존 이메일 사용자 확인
        user = User.objects.filter(
            email__iexact=email, deleted_at__isnull=True
        ).first()

        # 4. 신규 사용자 생성
        if not user:
            user = User.objects.create_user(
                email=email,
                nickname=nickname or email.split("@")[0],
                email_verified=True,
            )

        # 5. 소셜 계정 연결
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
        )

        return user

    @staticmethod
    @transaction.atomic
    def link_social_account(
            user: "UserModel", provider: str, social_user_info: Dict
    ) -> SocialAccount:
        provider_user_id = social_user_info["provider_user_id"]

        # 1. 다른 계정에 이미 연결된 경우
        if (
                SocialAccount.objects.filter(
                    provider=provider, provider_user_id=provider_user_id
                )
                        .exclude(user=user)
                        .exists()
        ):
            raise ValueError("이미 다른 계정에 연결된 소셜 계정입니다.")

        # 2. 현재 사용자에 이미 연결된 경우
        if SocialAccount.objects.filter(
                user=user, provider=provider, provider_user_id=provider_user_id
        ).exists():
            raise ValueError("이미 연결된 소셜 계정입니다.")

        return SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
        )

    @staticmethod
    @transaction.atomic
    def unlink_social_account(user: "UserModel", provider: str) -> None:

        social_account = SocialAccount.objects.get(
            user=user,
            provider=provider,
        )
        social_account.delete()

    @staticmethod
    def get_linked_providers(user: "UserModel") -> list[str]:

        return list(
            SocialAccount.objects.filter(user=user).values_list(
                "provider", flat=True
            )
        )

    @staticmethod
    def can_unlink_social_account(user: "UserModel", provider: str) -> bool:

        # 비밀번호가 없으면 (소셜 로그인만 사용) 마지막 소셜 계정 해제 불가
        if not user.has_usable_password():
            linked_count = SocialAccount.objects.filter(user=user).count()
            return linked_count > 1
        return True