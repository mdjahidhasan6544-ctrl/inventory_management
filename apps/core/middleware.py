"""
Organization Middleware — enforces multi-tenant data isolation.

Sets `request.organization` based on the authenticated user.
Works with both Django session auth and DRF JWT/force_authenticate.

Strategy:
  - Initialize request.organization = None in process_request
  - Skip public paths entirely
  - For non-public paths, organization resolution is deferred
    to a DRF mixin (TenantViewSetMixin) because DRF authentication
    runs AFTER Django middleware
  - For Django admin / session-auth paths, set organization early
"""

import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Paths that must be accessible without an organization context
PUBLIC_PREFIXES = (
    "/admin/",
    "/api/v1/auth/",
)


class OrganizationMiddleware:
    """Initialize request.organization for every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None

        # Skip for public paths
        if any(request.path.startswith(p) for p in PUBLIC_PREFIXES):
            return self.get_response(request)

        # For session-authenticated users (Django admin)
        if hasattr(request, "user") and request.user.is_authenticated:
            org = getattr(request.user, "organization", None)
            if org and org.is_active:
                request.organization = org

        return self.get_response(request)
