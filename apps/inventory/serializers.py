"""
Inventory Serializers — Products, Categories, Warehouses, Transactions.
"""

from rest_framework import serializers

from apps.inventory.models import (
    Category,
    InventoryTransaction,
    Product,
    Warehouse,
)


# =============================================================================
# Category
# =============================================================================


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "product_count",
            "children",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_product_count(self, obj):
        return obj.products.count()

    def get_children(self, obj):
        children = obj.children.all()
        return CategoryListSerializer(children, many=True).data


class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for nested/list views."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "parent"]

    def validate_parent(self, value):
        if value and value.organization_id != self.context["request"].organization.id:
            raise serializers.ValidationError(
                "Parent category must belong to the same organization."
            )
        return value


# =============================================================================
# Warehouse
# =============================================================================


class WarehouseSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "code",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "is_active",
            "product_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_product_count(self, obj):
        return obj.products.count()


class WarehouseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = [
            "name",
            "code",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "is_active",
        ]


# =============================================================================
# Product
# =============================================================================


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=None
    )
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "barcode",
            "description",
            "category",
            "category_name",
            "warehouse",
            "warehouse_name",
            "unit_price",
            "cost_price",
            "quantity",
            "low_stock_threshold",
            "unit",
            "is_active",
            "is_low_stock",
            "stock_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "quantity",  # managed via transactions only
            "created_at",
            "updated_at",
        ]


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "barcode",
            "description",
            "category",
            "warehouse",
            "unit_price",
            "cost_price",
            "low_stock_threshold",
            "unit",
            "is_active",
        ]

    def validate_category(self, value):
        if value and value.organization_id != self.context["request"].organization.id:
            raise serializers.ValidationError(
                "Category must belong to the same organization."
            )
        return value

    def validate_warehouse(self, value):
        if value and value.organization_id != self.context["request"].organization.id:
            raise serializers.ValidationError(
                "Warehouse must belong to the same organization."
            )
        return value


# =============================================================================
# Inventory Transaction
# =============================================================================


class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name", read_only=True
    )
    warehouse_name = serializers.CharField(
        source="warehouse.name", read_only=True, default=None
    )
    performed_by_username = serializers.CharField(
        source="performed_by.username", read_only=True, default=None
    )
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )

    class Meta:
        model = InventoryTransaction
        fields = [
            "id",
            "product",
            "product_name",
            "warehouse",
            "warehouse_name",
            "performed_by",
            "performed_by_username",
            "transaction_type",
            "transaction_type_display",
            "quantity",
            "reference",
            "notes",
            "quantity_before",
            "quantity_after",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "performed_by",
            "quantity_before",
            "quantity_after",
            "created_at",
        ]


class InventoryTransactionCreateSerializer(serializers.ModelSerializer):
    """
    Create a transaction and update the Product's denormalized quantity.
    """

    class Meta:
        model = InventoryTransaction
        fields = [
            "product",
            "warehouse",
            "transaction_type",
            "quantity",
            "reference",
            "notes",
        ]

    def validate_product(self, value):
        if value.organization_id != self.context["request"].organization.id:
            raise serializers.ValidationError(
                "Product must belong to your organization."
            )
        return value

    def validate_warehouse(self, value):
        if value and value.organization_id != self.context["request"].organization.id:
            raise serializers.ValidationError(
                "Warehouse must belong to your organization."
            )
        return value

    def validate(self, attrs):
        product = attrs["product"]
        quantity = attrs["quantity"]
        tx_type = attrs["transaction_type"]

        # Outbound transactions require sufficient stock
        outbound_types = (
            InventoryTransaction.TransactionType.SALE,
            InventoryTransaction.TransactionType.TRANSFER_OUT,
        )
        if tx_type in outbound_types and quantity > 0:
            # For outbound, quantity should be sent as positive; we negate it
            if product.quantity < quantity:
                raise serializers.ValidationError(
                    {
                        "quantity": (
                            f"Insufficient stock. Available: {product.quantity}, "
                            f"requested: {quantity}."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        from django.db import transaction as db_transaction

        product = validated_data["product"]
        quantity = validated_data["quantity"]
        tx_type = validated_data["transaction_type"]

        # Determine sign: outbound types reduce stock
        outbound_types = (
            InventoryTransaction.TransactionType.SALE,
            InventoryTransaction.TransactionType.TRANSFER_OUT,
        )
        if tx_type in outbound_types:
            effective_quantity = -abs(quantity)
        else:
            effective_quantity = abs(quantity)

        with db_transaction.atomic():
            # Lock the product row
            product = Product.objects.select_for_update().get(pk=product.pk)

            quantity_before = product.quantity
            product.quantity += effective_quantity
            product.save(update_fields=["quantity", "updated_at"])

            inv_tx = InventoryTransaction.objects.create(
                organization=self.context["request"].organization,
                product=product,
                warehouse=validated_data.get("warehouse"),
                performed_by=self.context["request"].user,
                transaction_type=tx_type,
                quantity=effective_quantity,
                reference=validated_data.get("reference", ""),
                notes=validated_data.get("notes", ""),
                quantity_before=quantity_before,
                quantity_after=product.quantity,
            )

        return inv_tx
