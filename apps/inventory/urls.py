"""
Inventory URL routes — /api/v1/inventory/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    CategoryViewSet,
    InventoryTransactionViewSet,
    ProductViewSet,
    WarehouseViewSet,
)

app_name = "inventory"

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"warehouses", WarehouseViewSet, basename="warehouse")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"transactions", InventoryTransactionViewSet, basename="transaction")

urlpatterns = [
    path("", include(router.urls)),
]
