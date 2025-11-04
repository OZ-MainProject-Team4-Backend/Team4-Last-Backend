from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator

from .models import User, SocialAccount



#닉네임 검증
class NicknameValidateSerializer(serializers.Serializer):
    nickname = serializers.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9가-힣_]+$',
                message="닉네임은 영문, 숫자, 한글, 밑줄만 가능합니다."
            )
        ]
    )



#이메일 검증
class EmailSendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=64)  # 길이는 서비스에 따라 조정



# 회원가입
class SignupSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "nickname", "gender", "age_group"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate(self, data):
        pw = data.get("password")
        pwc = data.get("password_confirm")
        if pw != pwc:
            raise serializers.ValidationError({"password_confirm": "비밀번호가 일치하지 않습니다."})

        if not pw or len(pw) < 8:
            raise serializers.ValidationError({"password": "비밀번호는 최소 8자 이상이어야 합니다."})
        if " " in pw:
            raise serializers.ValidationError({"password": "비밀번호에 공백을 포함할 수 없습니다."})

        email = data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "이미 사용중인 이메일입니다."})

        nickname = data.get("nickname")
        if nickname and User.objects.filter(nickname__iexact=nickname).exists():
            raise serializers.ValidationError({"nickname": "이미 사용중인 닉네임입니다."})

        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        raw_pw = validated_data.pop("password")
        validated_data["password"] = make_password(raw_pw)
        return User.objects.create(**validated_data)



# 로그인
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        # authenticate가 email 기반으로 동작하려면 AUTH backend 설정 필요.
        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError("로그인 실패: 이메일 또는 비밀번호가 올바르지 않습니다.")
        if not getattr(user, "is_active", True):
            raise serializers.ValidationError("비활성화된 계정입니다.")
        data["user"] = user
        return data



# 유저 프로필
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "nickname", "gender", "age_group"]
        read_only_fields = ["id", "email"]



# 비밀번호 변경
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
            raise serializers.ValidationError({"current_password": "현재 비밀번호가 일치하지 않습니다."})


        if attrs.get("new_password") != attrs.get("new_password_confirm"):
            raise serializers.ValidationError({"new_password_confirm": "새 비밀번호와 확인 비밀번호가 일치하지 않습니다."})

        new_pw = attrs.get("new_password")
        if not new_pw or len(new_pw) < 8:
            raise serializers.ValidationError({"new_password": "비밀번호는 최소 8자 이상이어야 합니다."})
        if " " in new_pw:
            raise serializers.ValidationError({"new_password": "비밀번호에 공백을 포함할 수 없습니다."})

        return attrs

    def save(self, **kwargs):
        request = self.context.get("request")
        user = request.user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


#소셜 로그인
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
