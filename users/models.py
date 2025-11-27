from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User 모델
    - role: BORROWER / LENDER / ADMIN
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "관리자"
        BORROWER = "BORROWER", "차주"
        LENDER = "LENDER", "대주"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.BORROWER,
    )

    @property
    def is_borrower(self) -> bool:
        return self.role == self.Role.BORROWER

    @property
    def is_lender(self) -> bool:
        return self.role == self.Role.LENDER

    @property
    def is_admin_role(self) -> bool:
        """role 필드 상의 관리자 (superuser와 별개 개념)"""
        return self.role == self.Role.ADMIN
