"""
Admin configuration for Core app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.core.models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan", "is_active", "created_at")
    list_filter = ("plan", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "organization",
        "role",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_active", "organization")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Organization & Role",
            {
                "fields": ("organization", "role", "phone"),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Organization & Role",
            {
                "fields": ("organization", "role"),
            },
        ),
    )
