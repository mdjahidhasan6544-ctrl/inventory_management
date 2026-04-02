"""
Inventory Views — Products, Categories, Warehouses, Transactions.

Every queryset is scoped to `request.organization` for tenant isolation.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsOrgManager, IsOrganizationMember, ReadOnly
from apps.inventory.models import (
    Category,
    InventoryTransaction,
    Product,
    Warehouse,
)
from apps.inventory.serializers import (
    CategoryCreateUpdateSerializer,
    CategorySerializer,
    InventoryTransactionCreateSerializer,
    InventoryTransactionSerializer,
    ProductCreateUpdateSerializer,
    ProductSerializer,
    WarehouseCreateUpdateSerializer,
    WarehouseSerializer,
)


# =============================================================================
# Base Mixin
# =============================================================================


class TenantViewSetMixin:
    """Mixin that scopes querysets to the current organization."""

    def get_organization(self):
        return self.request.organization

    def perform_create(self, serializer):
        serializer.save(organization=self.get_organization())


# =============================================================================
# Category ViewSet
# =============================================================================


class CategoryViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    /api/v1/inventory/categories/

    CRUD for product categories. Managers+ can write; viewers can read.
    """

    permission_classes = [IsOrganizationMember, IsOrgManager | ReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["parent"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CategoryCreateUpdateSerializer
        return CategorySerializer

    def get_queryset(self):
        return (
            Category.objects
            .for_organization(self.get_organization())
            .select_related("parent")
            .prefetch_related("children")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            CategorySerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def roots(self, request):
        """GET /categories/roots/ — only top-level categories."""
        qs = self.get_queryset().filter(parent__isnull=True)
        serializer = CategorySerializer(qs, many=True)
        return Response(serializer.data)


# =============================================================================
# Warehouse ViewSet
# =============================================================================


class WarehouseViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    /api/v1/inventory/warehouses/

    CRUD for warehouses. Managers+ can write; viewers can read.
    """

    permission_classes = [IsOrganizationMember, IsOrgManager | ReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "country", "city"]
    search_fields = ["name", "code", "city"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return WarehouseCreateUpdateSerializer
        return WarehouseSerializer

    def get_queryset(self):
        return Warehouse.objects.for_organization(self.get_organization())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            WarehouseSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Product ViewSet
# =============================================================================


class ProductViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    /api/v1/inventory/products/

    CRUD for products. Managers+ can write; viewers can read.
    Quantity is managed exclusively through inventory transactions.
    """

    permission_classes = [IsOrganizationMember, IsOrgManager | ReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "warehouse", "is_active", "unit"]
    search_fields = ["name", "sku", "barcode", "description"]
    ordering_fields = ["name", "sku", "quantity", "unit_price", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductCreateUpdateSerializer
        return ProductSerializer

    def get_queryset(self):
        return (
            Product.objects
            .for_organization(self.get_organization())
            .select_related("category", "warehouse")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            ProductSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """GET /products/low_stock/ — products below their threshold."""
        qs = self.get_queryset().filter(is_active=True)
        # Filter in Python because `is_low_stock` is a property, but
        # we can approximate with a DB query:
        from django.db.models import F
        qs = qs.filter(quantity__lte=F("low_stock_threshold"))
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProductSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        """GET /products/{id}/transactions/ — all transactions for a product."""
        product = self.get_object()
        txs = InventoryTransaction.objects.filter(
            organization=self.get_organization(),
            product=product,
        ).select_related("warehouse", "performed_by").order_by("-created_at")
        page = self.paginate_queryset(txs)
        if page is not None:
            serializer = InventoryTransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = InventoryTransactionSerializer(txs, many=True)
        return Response(serializer.data)


# =============================================================================
# Inventory Transaction ViewSet
# =============================================================================


class InventoryTransactionViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    /api/v1/inventory/transactions/

    List/create inventory transactions. Transactions are immutable —
    update and delete are disabled.
    """

    permission_classes = [IsOrganizationMember, IsOrgManager | ReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["product", "warehouse", "transaction_type", "performed_by"]
    search_fields = ["reference", "notes", "product__name"]
    ordering_fields = ["created_at", "quantity"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "head", "options"]  # No PUT/PATCH/DELETE

    def get_serializer_class(self):
        if self.action == "create":
            return InventoryTransactionCreateSerializer
        return InventoryTransactionSerializer

    def get_queryset(self):
        return (
            InventoryTransaction.objects
            .for_organization(self.get_organization())
            .select_related("product", "warehouse", "performed_by")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        return Response(
            InventoryTransactionSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
        )
