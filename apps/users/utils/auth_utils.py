import random

EMAIL_VERIF_CODE_TTL = 300  # 5분
EMAIL_PREVER_TTL = 1800  # 30분
EMAIL_VERIF_RESEND_TTL = 60  # 1분
EMAIL_VERIF_MAX_PER_HOUR = 5


def gen_code(n=6):
    """n자리 숫자 인증코드 생성"""
    return "".join(str(random.randint(0, 9)) for _ in range(n))


def key_verif(email: str):
    """이메일 인증코드 캐시 키"""
    return f"email_verif:{email.lower()}"


def key_preverified(email: str):
    """이메일 사전 검증 캐시 키"""
    return f"email_preverified:{email.lower()}"


def key_resend(email: str):
    """이메일 재전송 제한 캐시 키"""
    return f"email_verif_resend:{email.lower()}"


def key_count(email: str):
    """이메일 발송 횟수 카운트 캐시 키"""
    return f"email_verif_count:{email.lower()}"


def key_nickname_valid(nickname: str):
    """닉네임 유효성 캐시 키"""
    return f"nickname_valid:{nickname.lower()}"


def get_user_data(user):
    """사용자 데이터 포맷팅"""
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "gender": getattr(user, "gender", None),
        "age_group": getattr(user, "age_group", None),
        "is_verified": user.email_verified,
        "favorite_regions": getattr(user, "favorite_regions", None) or [],
        "created_at": (
            user.created_at.isoformat() if hasattr(user, "created_at") else None
        ),
    }
