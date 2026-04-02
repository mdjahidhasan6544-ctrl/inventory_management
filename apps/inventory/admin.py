"""
Admin configuration for Inventory app.
"""

from django.contrib import admin

from apps.inventory.models import (
    Category,
    InventoryTransaction,
    Product,
    Warehouse,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "organization", "parent", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "city", "country", "is_active")
    list_filter = ("organization", "is_active", "country")
    search_fields = ("name", "code", "city")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "organization",
        "category",
        "warehouse",
        "quantity",
        "unit_price",
        "is_active",
    )
    list_filter = ("organization", "category", "warehouse", "is_active", "unit")
    search_fields = ("name", "sku", "barcode")
    readonly_fields = ("id", "quantity", "created_at", "updated_at")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "transaction_type",
        "quantity",
        "quantity_before",
        "quantity_after",
        "performed_by",
        "created_at",
    )
    list_filter = ("organization", "transaction_type")
    search_fields = ("product__name", "reference", "notes")
    readonly_fields = (
        "id",
        "organization",
        "product",
        "warehouse",
        "performed_by",
        "transaction_type",
        "quantity",
        "quantity_before",
        "quantity_after",
        "reference",
        "notes",
        "created_at",
    )

    def has_change_permission(self, request, obj=None):
        return False  # Transactions are immutable

    def has_delete_permission(self, request, obj=None):
        return False
