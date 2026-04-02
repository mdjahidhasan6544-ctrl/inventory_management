"""
Root URL configuration for Inventory Management SaaS.

Routes:
  /api/v1/auth/     — Authentication (JWT obtain/refresh/logout, registration)
  /api/v1/core/     — Organization & user management
  /api/v1/inventory/ — Products, categories, warehouses, transactions
  /admin/           — Django admin panel
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.core.urls_auth")),
    path("api/v1/core/", include("apps.core.urls")),
    path("api/v1/inventory/", include("apps.inventory.urls")),
]
