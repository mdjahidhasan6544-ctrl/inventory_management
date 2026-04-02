"""
Core Models — Users and Organizations for multi-tenant SaaS.

Architecture:
  Organization is the tenant boundary. Every data query is scoped to
  the requesting user's organization via middleware + queryset filtering.

  User extends AbstractUser and carries a foreign key to Organization
  along with a role enum for RBAC within the tenant.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


# =============================================================================
# Abstract Base
# =============================================================================


class TimeStampedModel(models.Model):
    """Abstract base with created/updated timestamps and UUID pk."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


# =============================================================================
# Organization (Tenant)
# =============================================================================


class Organization(TimeStampedModel):
    """
    SaaS tenant. All inventory data is scoped to an organization.

    Fields:
      name        — Display name (e.g. "Acme Corp")
      slug        — URL-safe unique identifier
      is_active   — Soft-disable an entire tenant
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    # Subscription / plan metadata (extensible)
    plan = models.CharField(
        max_length=20,
        choices=[
            ("free", "Free"),
            ("starter", "Starter"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ],
        default="free",
    )
    max_users = models.PositiveIntegerField(default=5)
    max_warehouses = models.PositiveIntegerField(default=2)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name


# =============================================================================
# User
# =============================================================================


class User(AbstractUser):
    """
    Custom user linked to an Organization for multi-tenancy.

    Role-based access:
      owner   — Full control, can manage billing & users
      admin   — Manage inventory settings & users
      manager — Manage products, warehouses, transactions
      viewer  — Read-only access
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members",
        null=True,
        blank=True,
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    phone = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["organization", "role"]),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.organization})"

    @property
    def is_org_admin(self):
        return self.role in (self.Role.OWNER, self.Role.ADMIN)
