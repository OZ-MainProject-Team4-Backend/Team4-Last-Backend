from typing import Dict, Optional

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from rest_framework import serializers

from .models import SocialAccount, User


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


phone_validator = RegexValidator(
    regex=r'^[0-9+\-]{9,20}$',
    message="전화번호 형식이 올바르지 않습니다. (숫자, +, - 허용, 9~20자리)",
)


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
    if v in ("60", "60대 이상", "60+", "60s"):
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
        return "Woman"
    if v in ("male", "man", "남성", "m"):
        return "Man"
    return "0"


class SignupSerializer(serializers.ModelSerializer):
    age = serializers.CharField(write_only=True, required=False, allow_blank=True)
    gender = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone = serializers.CharField(
        required=False, allow_blank=True, validators=[phone_validator]
    )
    password_confirm = serializers.CharField(write_only=True)
    nickname = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "nickname",
            "name",
            "age",
            "gender",
            "phone",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
        }

    def validate(self, data: Dict):
        pw = data.get("password")
        pwc = data.get("password_confirm")

        # 비밀번호 일치 확인
        if pw != pwc:
            raise serializers.ValidationError(
                {"password_confirm": "비밀번호가 일치하지 않습니다."}
            )

        # 길이 확인
        if not pw or len(pw) < 6 or len(pw) > 20:
            raise serializers.ValidationError(
                {"password": "비밀번호는 6자 이상 20자 이하로 입력해야 합니다."}
            )

        # 공백 확인
        if " " in pw:
            raise serializers.ValidationError(
                {"password": "비밀번호에 공백을 포함할 수 없습니다."}
            )

        # 대문자, 소문자, 숫자 포함 확인
        if (
            not any(c.islower() for c in pw)
            or not any(c.isupper() for c in pw)
            or not any(c.isdigit() for c in pw)
        ):
            raise serializers.ValidationError(
                {"password": "비밀번호는 영어 대문자, 소문자, 숫자를 조합해야 합니다."}
            )

        # 영어+숫자만 허용 확인 (특수문자 제외)
        if not all(c.isalnum() for c in pw):
            raise serializers.ValidationError(
                {"password": "비밀번호는 영어와 숫자만 사용할 수 있습니다."}
            )

        # 이메일 중복 확인
        email = data.get("email")
        if (
            email
            and User.objects.filter(
                email__iexact=email, deleted_at__isnull=True
            ).exists()
        ):
            raise serializers.ValidationError({"email": "이미 사용중인 이메일입니다."})

        # 닉네임 중복 확인
        nickname = data.get("nickname")
        if (
            nickname
            and User.objects.filter(
                nickname__iexact=nickname, deleted_at__isnull=True
            ).exists()
        ):
            raise serializers.ValidationError(
                {"nickname": "이미 사용중인 닉네임입니다."}
            )

        return data

    def create(self, validated_data: Dict) -> User:
        validated_data.pop("password_confirm", None)
        raw_pw = validated_data.pop("password")
        raw_age = validated_data.pop("age", None)
        raw_gender = validated_data.pop("gender", None)
        age_group = map_age_to_group(raw_age)
        gender_choice = map_gender(raw_gender)

        extra = {
            "nickname": validated_data.get("nickname"),
            "name": validated_data.get("name"),
            "phone": validated_data.get("phone"),
        }
        if age_group:
            extra["age_group"] = age_group
        if gender_choice:
            extra["gender"] = gender_choice

        email = validated_data.get("email")
        if not isinstance(email, str):
            raise serializers.ValidationError({"email": "이메일이 누락되었습니다."})

        try:
            user = User.objects.create_user(email, raw_pw, **extra)
            return user
        except TypeError:
            try:
                user = User.objects.create_user(email=email, password=raw_pw, **extra)
                return user
            except Exception:
                validated_password = make_password(raw_pw)
                user = User(
                    email=email,
                    nickname=extra.get("nickname"),
                    name=extra.get("name"),
                    phone=extra.get("phone"),
                    age_group=extra.get("age_group"),
                    gender=extra.get("gender"),
                )
                user.password = validated_password
                user.save()
                return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError(
                "로그인 실패: 이메일 또는 비밀번호가 올바르지 않습니다."
            )
        if not getattr(user, "is_active", True):
            raise serializers.ValidationError("비활성화된 계정입니다.")
        data["user"] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "nickname", "gender", "age_group"]
        read_only_fields = ["id", "email"]


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
        if not any(c.islower() for c in new_pw) or not any(c.isupper() for c in new_pw):
            raise serializers.ValidationError(
                {"new_password": "비밀번호는 영어 대문자와 소문자를 조합해야 합니다."}
            )
        if not all(c.isalpha() for c in new_pw):
            raise serializers.ValidationError(
                {"new_password": "비밀번호는 영어만 사용할 수 있습니다."}
            )
        return attrs

    def save(self, **kwargs):
        request = self.context.get("request")
        user = request.user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class UserDeleteSerializer(serializers.Serializer):
    """회원탈퇴 - 비밀번호 확인 불필요"""

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
