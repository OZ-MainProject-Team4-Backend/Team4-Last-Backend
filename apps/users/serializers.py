from typing import TYPE_CHECKING, Dict, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from rest_framework import serializers

from .models import SocialAccount, Token

# ==============================
# 런타임용 User 모델
# ==============================
UserModel = get_user_model()

# ==============================
# 타입체크용 User 모델
# ==============================
if TYPE_CHECKING:
    from apps.users.models import User


# ==============================
# 유틸 함수
# ==============================
def map_age_to_group(age_value: Optional[str]) -> Optional[str]:
    if not age_value:
        return None
    v = str(age_value).strip().lower()
    if v in ("10", "10대", "teen", "teens", "10s"):
        return "10"
    if v in ("20", "20대", "twenty", "20s"):
        return "20"
    if v in ("30", "30대", "thirty", "30s"):
        return "30"
    if v in ("40", "40대", "forty", "40s"):
        return "40"
    if v in ("50", "50대", "fifty", "50s"):
        return "50"
    if v in ("60", "60대 이상", "60+", "60s", "other"):
        return "60+"
    try:
        n = int(v)
        if 10 <= n < 20:
            return "10"
        if 20 <= n < 30:
            return "20"
        if 30 <= n < 40:
            return "30"
        if 40 <= n < 50:
            return "40"
        if 50 <= n < 60:
            return "50"
        if n >= 60:
            return "60+"
    except Exception:
        pass
    return None


def map_gender(gender_value: Optional[str]) -> Optional[str]:
    if not gender_value:
        return None
    v = str(gender_value).strip().lower()
    if v in ("female", "woman", "여성", "w", "f"):
        return "W"
    if v in ("male", "man", "남성", "m"):
        return "M"
    return "0"


# ==============================
# Serializer 정의
# ==============================
class NicknameValidateSerializer(serializers.Serializer):
    nickname = serializers.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9가-힣_]+$',
                message="닉네임은 영문, 숫자, 한글, 밑줄만 가능합니다.",
            )
        ],
    )


class EmailSendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=64)


class SignupSerializer(serializers.ModelSerializer):
    age = serializers.CharField(write_only=True, required=False, allow_blank=True)
    gender = serializers.CharField(write_only=True, required=False, allow_blank=True)
    nickname = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = UserModel
        fields = [
            "email",
            "password",
            "nickname",
            "name",
            "age",
            "gender",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
        }

    def validate(self, data: Dict):
        pw = data.get("password")

        if not pw or len(pw) < 6 or len(pw) > 20:
            raise serializers.ValidationError(
                {"password": "비밀번호는 6자 이상 20자 이하로 입력해야 합니다."}
            )

        if " " in pw:
            raise serializers.ValidationError(
                {"password": "비밀번호에 공백을 포함할 수 없습니다."}
            )

        if not any(c.islower() for c in pw) or not any(c.isdigit() for c in pw):
            raise serializers.ValidationError(
                {"password": "비밀번호는 영어 소문자, 숫자를 조합해야 합니다."}
            )

        if not all(c.isalnum() for c in pw):
            raise serializers.ValidationError(
                {"password": "비밀번호는 영어와 숫자만 사용할 수 있습니다."}
            )

        nickname = data.get("nickname")
        if (
            nickname
            and UserModel.objects.filter(
                nickname__iexact=nickname, deleted_at__isnull=True
            ).exists()
        ):
            raise serializers.ValidationError(
                {"nickname": "이미 사용중인 닉네임입니다."}
            )

        return data

    def create(self, validated_data: Dict) -> "User":
        raw_pw = validated_data.pop("password")
        raw_age = validated_data.pop("age", None)
        raw_gender = validated_data.pop("gender", None)

        age_group = map_age_to_group(raw_age)
        gender_choice = map_gender(raw_gender)

        extra = {
            "nickname": validated_data.get("nickname"),
            "name": validated_data.get("name"),
        }
        if age_group:
            extra["age_group"] = age_group
        if gender_choice:
            extra["gender"] = gender_choice

        email = validated_data.get("email")
        if not isinstance(email, str):
            raise serializers.ValidationError({"email": "이메일이 누락되었습니다."})

        user = UserModel.objects.create_user(email=email, password=raw_pw, **extra)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    isAutoLogin = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = UserModel.objects.get(email__iexact=email, deleted_at__isnull=True)
        except UserModel.DoesNotExist:
            raise serializers.ValidationError(
                "로그인 실패: 이메일 또는 비밀번호가 올바르지 않습니다."
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                "로그인 실패: 이메일 또는 비밀번호가 올바르지 않습니다."
            )

        if not getattr(user, "is_active", True):
            raise serializers.ValidationError("비활성화된 계정입니다.")

        if not getattr(user, "email_verified", False):
            raise serializers.ValidationError("이메일 인증이 필요합니다.")

        if getattr(user, "deleted_at", None):
            raise serializers.ValidationError("탈퇴한 계정입니다.")

        data["user"] = user
        data["isAutoLogin"] = bool(data.get("isAutoLogin", False))
        return data


class LoginResponseSerializer(serializers.Serializer):
    user = serializers.DictField()
    access = serializers.CharField()
    access_expires_at = serializers.DateTimeField()
    is_auto_login = serializers.BooleanField()


class UserProfileSerializer(serializers.ModelSerializer):
    # ✅ age_group과 gender 필드 명시적으로 정의
    age_group = serializers.CharField(
        required=False,
        allow_null=True,  # ✅ null 허용
        allow_blank=True,  # ✅ 빈 문자열 허용
    )
    gender = serializers.CharField(
        required=False,
        allow_null=True,  # ✅ null 허용
        allow_blank=True,  # ✅ 빈 문자열 허용
    )

    class Meta:
        model = UserModel
        fields = ["id", "email", "nickname", "name", "gender", "age_group"]
        read_only_fields = ["id", "email"]

    def update(self, instance, validated_data):
        # ✅ gender 처리 수정
        gender = validated_data.pop("gender", None)
        if gender:  # None이나 빈 문자열이 아닐 때만 처리
            gender_map = {
                "woman": "W",
                "man": "M",
                "여성": "W",
                "남성": "M",
                "w": "W",
                "m": "M",
                "W": "W",
                "M": "M",
            }
            instance.gender = gender_map.get(gender, "0")

        # ✅ age_group 처리 수정
        age_group = validated_data.pop("age_group", None)
        if age_group:  # None이나 빈 문자열이 아닐 때만 처리
            mapped_age = map_age_to_group(age_group)
            if mapped_age:
                instance.age_group = mapped_age

        # 나머지 필드 업데이트
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class FavoriteRegionsSerializer(serializers.Serializer):
    favorite_regions = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=True,
        max_length=3,
        help_text="사용자가 등록한 즐겨찾는 지역 (최대 3개)",
    )

    def validate_favorite_regions(self, value):
        if len(value) > 3:
            raise serializers.ValidationError(
                "지역은 최대 3개까지만 등록할 수 있습니다."
            )

        if any(not region.strip() for region in value):
            raise serializers.ValidationError("유효하지 않은 지역이 있습니다.")

        if len(value) != len(set(value)):
            raise serializers.ValidationError("중복된 지역이 있습니다.")

        return value


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None or not hasattr(request, "user"):
            raise serializers.ValidationError("요청 정보가 올바르지 않습니다.")

        user = request.user
        if not user.check_password(attrs.get("current_password", "")):
            raise serializers.ValidationError(
                {"current_password": "현재 비밀번호가 일치하지 않습니다."}
            )

        if attrs.get("new_password") != attrs.get("new_password_confirm"):
            raise serializers.ValidationError(
                {
                    "new_password_confirm": "새 비밀번호와 확인 비밀번호가 일치하지 않습니다."
                }
            )

        new_pw = attrs.get("new_password")

        if not new_pw or len(new_pw) < 6 or len(new_pw) > 20:
            raise serializers.ValidationError(
                {"new_password": "비밀번호는 6자 이상 20자 이하로 입력해야 합니다."}
            )

        if " " in new_pw:
            raise serializers.ValidationError(
                {"new_password": "비밀번호에 공백을 포함할 수 없습니다."}
            )

        if not any(c.islower() for c in new_pw) or not any(c.isdigit() for c in new_pw):
            raise serializers.ValidationError(
                {"new_password": "비밀번호는 영어 소문자와 숫자를 조합해야 합니다."}
            )

        if not all(c.isalnum() for c in new_pw):
            raise serializers.ValidationError(
                {"new_password": "비밀번호는 영어와 숫자만 사용할 수 있습니다."}
            )

        return attrs

    def save(self, **kwargs):
        request = self.context.get("request")
        user = request.user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class UserDeleteSerializer(serializers.Serializer):
    pass


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ["id", "user", "provider", "provider_user_id", "connected_at"]
        read_only_fields = ["connected_at"]


class SocialLoginSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

    def validate_token(self, value):
        if not value.strip():
            raise serializers.ValidationError("유효하지 않은 토큰입니다.")
        return value


class SocialLinkSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

    def validate_token(self, value):
        if not value.strip():
            raise serializers.ValidationError("유효하지 않은 토큰입니다.")
        return value


class SocialUnlinkSerializer(serializers.Serializer):
    pass


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)

    def validate_refresh(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Refresh 토큰이 필요합니다.")
        return value.strip()


class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = [
            "id",
            "user",
            "access_jwt",
            "refresh_jwt",
            "access_expires_at",
            "refresh_expires_at",
            "revoked",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "access_jwt",
            "refresh_jwt",
            "access_expires_at",
            "refresh_expires_at",
            "created_at",
        ]


class AccessTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)
    expires_in = serializers.IntegerField(required=False)


class TokenRevokeSerializer(serializers.Serializer):
    pass
