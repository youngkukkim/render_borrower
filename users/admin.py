from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Django 기본 UserAdmin에 role 필드만 추가한 버전
    """

    fieldsets = BaseUserAdmin.fieldsets + (
        ("추가 정보", {"fields": ("role",)}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("추가 정보", {"fields": ("role",)}),
    )

    list_display = BaseUserAdmin.list_display + ("role",)
