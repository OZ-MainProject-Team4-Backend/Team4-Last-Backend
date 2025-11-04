from django.conf import settings
from django.core.mail import EmailMessage


def send_verification_email(email, code):
    subject = "이메일 인증 코드 안내"

    message = f"""
    안녕하세요!
    아래의 인증 코드를 입력하시면 이메일 인증이 완료됩니다.

    인증 코드: {code}

    인증 코드는 5분 후 만료됩니다.
    """

    email_message = EmailMessage(
        subject, message, settings.DEFAULT_FROM_EMAIL, [email]
    )
    email_message.send(fail_silently=False)

