import logging
from django.contrib.auth import get_user_model

from ..models import SocialAccount
from ..utils.social_auth import verify_social_token, SocialTokenInvalidError

User = get_user_model()
logger = logging.getLogger(__name__)


class SocialAuthService:
    """소셜 인증 관련 서비스"""

    @staticmethod
    def get_or_create_user_from_social(provider: str, social_user_info: dict):
        """소셜 사용자 정보로부터 사용자 객체 조회 또는 생성"""
        provider_user_id = social_user_info.get("provider_user_id")
        email = social_user_info.get("email")
        nickname = social_user_info.get("nickname")

        try:
            social_account = SocialAccount.objects.select_related("user").get(
                provider=provider, provider_user_id=provider_user_id
            )
            return social_account.user
        except SocialAccount.DoesNotExist:
            pass

        if email:
            try:
                user = User.objects.get(email__iexact=email, deleted_at__isnull=True)
            except User.DoesNotExist:
                user = None
        else:
            user = None

        if not user:
            user = User.objects.create_user(
                email=email or f"{provider}_{provider_user_id}@social.local",
                nickname=nickname or f"{provider}_{provider_user_id}",
            )
            user.email_verified = True
            user.save(update_fields=["email_verified"])

        SocialAccount.objects.get_or_create(
            provider=provider,
            provider_user_id=provider_user_id,
            defaults={"user": user},
        )

        return user

    @staticmethod
    def link_social_account(user, provider: str, social_user_info: dict):
        """기존 사용자에게 소셜 계정 연결"""
        provider_user_id = social_user_info.get("provider_user_id")

        existing_account = SocialAccount.objects.filter(
            provider=provider, provider_user_id=provider_user_id
        ).first()

        if existing_account and existing_account.user_id != user.id:
            raise ValueError("이미 다른 계정에 연결된 소셜 계정입니다")

        SocialAccount.objects.get_or_create(
            provider=provider,
            provider_user_id=provider_user_id,
            defaults={"user": user},
        )

    @staticmethod
    def unlink_social_account(user, provider: str):
        """사용자로부터 소셜 계정 연결 해제"""
        social_account = SocialAccount.objects.get(user=user, provider=provider)
        social_account.delete()

    @staticmethod
    def get_user_social_accounts(user):
        """사용자가 연결한 모든 소셜 계정 조회"""
        accounts = SocialAccount.objects.filter(user=user).values_list(
            "provider", flat=True
        )
        return list(accounts)