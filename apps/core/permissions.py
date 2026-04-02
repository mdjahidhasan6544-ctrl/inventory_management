"""
Custom permissions for multi-tenant RBAC.

These are DRF-level permissions applied on ViewSets.
Tenant isolation is enforced at the queryset level in views,
but these permissions add role-based access control on top.
"""

from rest_framework.permissions import BasePermission

from apps.core.models import User


class IsOrganizationMember(BasePermission):
    """
    User must belong to an active organization.

    Also resolves and sets request.organization if not already set
    by middleware (DRF authentication runs after Django middleware).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Resolve organization if middleware couldn't (DRF auth runs later)
        if getattr(request, "organization", None) is None:
            org = getattr(request.user, "organization", None)
            if org is not None and org.is_active:
                request.organization = org

        return getattr(request, "organization", None) is not None


class IsOrgAdmin(BasePermission):
    """User must be an owner or admin within their organization."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in (User.Role.OWNER, User.Role.ADMIN)


class IsOrgManager(BasePermission):
    """User must be at least a manager (owner, admin, or manager)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in (
            User.Role.OWNER,
            User.Role.ADMIN,
            User.Role.MANAGER,
        )


class IsOrgOwner(BasePermission):
    """User must be the organization owner."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == User.Role.OWNER


class ReadOnly(BasePermission):
    """Allow only safe (read-only) HTTP methods."""

    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")
