"""
Core URL routes — /api/v1/core/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.views import OrganizationDetailView, UserViewSet

app_name = "core"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("organization/", OrganizationDetailView.as_view(), name="organization-detail"),
    path("", include(router.urls)),
]
