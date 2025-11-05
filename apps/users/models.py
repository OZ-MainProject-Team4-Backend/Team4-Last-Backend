from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("email required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    AGE_GROUP_CHOICES = (
        ("10", "10대"),
        ("20", "20대"),
        ("30", "30대"),
        ("40", "40대"),
        ("50", "50대"),
        ("60+", "60대 이상"),
    )
    GENDER_CHOICES = (
        ("Woman", "여성"),
        ("Man", "남성"),
        ("0", "기타"),
    )

    # phone validator: 숫자, +, - 허용, 9~20자
    phone_validator = RegexValidator(
        regex=r'^[0-9+\-]{9,20}$',
        message="전화번호 형식이 올바르지 않습니다. (숫자, +, - 허용, 9~20자리)"
    )

    id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=150, unique=True, null=False, db_index=True)
    password = models.CharField(max_length=255)
    name = models.CharField(max_length=100, blank=True, null=True)
    nickname = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    # 추가된 필드: phone
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        validators=[phone_validator],
        help_text="국가번호 포함 가능. 숫자, +, - 허용"
    )

    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True, null=True
    )
    age_group = models.CharField(
        max_length=10,
        choices=AGE_GROUP_CHOICES,
        blank=True,
        null=True,
        verbose_name="연령대",
    )

    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["nickname"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.email

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active"])

    def restore(self):
        self.deleted_at = None
        self.is_active = True
        self.save(update_fields=["deleted_at", "is_active"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class SocialAccount(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="social_accounts"
    )
    provider = models.CharField(max_length=20)
    provider_user_id = models.CharField(max_length=200)
    connected_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("provider", "provider_user_id")
        db_table = "social_accounts"
        verbose_name = "Social Account"
        verbose_name_plural = "Social Accounts"

    def __str__(self):
        return f"{self.provider} - {self.user.email}"
