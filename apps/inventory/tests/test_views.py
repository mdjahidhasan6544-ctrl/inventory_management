"""
Tests for inventory API endpoints — Categories, Warehouses, Products, Transactions.
"""

import pytest
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from apps.inventory.models import (
    Category,
    InventoryTransaction,
    Product,
    Warehouse,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def category(organization):
    return Category.objects.create(
        organization=organization,
        name="Electronics",
        slug="electronics",
    )


@pytest.fixture
def warehouse(organization):
    return Warehouse.objects.create(
        organization=organization,
        name="Main Warehouse",
        code="WH-001",
        city="New York",
    )


@pytest.fixture
def product(organization, category, warehouse):
    return Product.objects.create(
        organization=organization,
        category=category,
        warehouse=warehouse,
        name="Laptop",
        sku="LAP-001",
        unit_price=Decimal("999.99"),
        cost_price=Decimal("750.00"),
        quantity=50,
    )


@pytest.fixture
def other_org_product(other_organization):
    return Product.objects.create(
        organization=other_organization,
        name="Other Product",
        sku="OTH-001",
        unit_price=Decimal("1.00"),
        quantity=10,
    )


# =============================================================================
# Category Tests
# =============================================================================


@pytest.mark.django_db
class TestCategoryAPI:
    list_url = reverse("inventory:category-list")

    def detail_url(self, cat_id):
        return reverse("inventory:category-detail", kwargs={"pk": cat_id})

    def test_list_categories(self, authenticated_client, category):
        response = authenticated_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_create_category(self, authenticated_client):
        data = {"name": "Clothing", "slug": "clothing", "description": "Apparel"}
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Clothing"

    def test_viewer_cannot_create(self, viewer_client):
        data = {"name": "Blocked", "slug": "blocked"}
        response = viewer_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_can_read(self, viewer_client, category):
        response = viewer_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK

    def test_update_category(self, authenticated_client, category):
        response = authenticated_client.patch(
            self.detail_url(category.id), {"name": "Updated Electronics"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Electronics"

    def test_delete_category(self, authenticated_client, category):
        response = authenticated_client.delete(self.detail_url(category.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_tenant_isolation(self, other_org_client, category):
        """User from another org should NOT see this org's categories."""
        response = other_org_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        names = [c["name"] for c in response.data["results"]]
        assert category.name not in names

    def test_roots_action(self, authenticated_client, category):
        url = reverse("inventory:category-roots")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Warehouse Tests
# =============================================================================


@pytest.mark.django_db
class TestWarehouseAPI:
    list_url = reverse("inventory:warehouse-list")

    def detail_url(self, wh_id):
        return reverse("inventory:warehouse-detail", kwargs={"pk": wh_id})

    def test_list_warehouses(self, authenticated_client, warehouse):
        response = authenticated_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_create_warehouse(self, authenticated_client):
        data = {
            "name": "West Warehouse",
            "code": "WH-WEST",
            "city": "Los Angeles",
            "country": "US",
        }
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "West Warehouse"

    def test_viewer_cannot_create(self, viewer_client):
        data = {"name": "Blocked", "code": "BL-001"}
        response = viewer_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tenant_isolation(self, other_org_client, warehouse):
        response = other_org_client.get(self.list_url)
        names = [w["name"] for w in response.data["results"]]
        assert warehouse.name not in names


# =============================================================================
# Product Tests
# =============================================================================


@pytest.mark.django_db
class TestProductAPI:
    list_url = reverse("inventory:product-list")

    def detail_url(self, prod_id):
        return reverse("inventory:product-detail", kwargs={"pk": prod_id})

    def test_list_products(self, authenticated_client, product):
        response = authenticated_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_create_product(self, authenticated_client, category, warehouse):
        data = {
            "name": "Monitor",
            "sku": "MON-001",
            "unit_price": "299.99",
            "cost_price": "200.00",
            "category": str(category.id),
            "warehouse": str(warehouse.id),
        }
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Monitor"

    def test_product_created_with_zero_quantity(self, authenticated_client):
        data = {
            "name": "New Item",
            "sku": "NEW-001",
            "unit_price": "50.00",
        }
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["quantity"] == 0

    def test_viewer_cannot_create(self, viewer_client):
        data = {"name": "Blocked", "sku": "BLK-001", "unit_price": "10.00"}
        response = viewer_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tenant_isolation(self, other_org_client, product):
        response = other_org_client.get(self.list_url)
        skus = [p["sku"] for p in response.data["results"]]
        assert product.sku not in skus

    def test_low_stock_action(self, authenticated_client, organization):
        Product.objects.create(
            organization=organization,
            name="Low Item",
            sku="LOW-001",
            unit_price=Decimal("5.00"),
            quantity=2,
            low_stock_threshold=10,
        )
        url = reverse("inventory:product-low-stock")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        skus = [p["sku"] for p in response.data["results"]]
        assert "LOW-001" in skus

    def test_product_transactions_action(self, authenticated_client, product, organization, owner_user):
        InventoryTransaction.objects.create(
            organization=organization,
            product=product,
            performed_by=owner_user,
            transaction_type="purchase",
            quantity=10,
            quantity_before=50,
            quantity_after=60,
        )
        url = reverse("inventory:product-transactions", kwargs={"pk": product.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Transaction Tests
# =============================================================================


@pytest.mark.django_db
class TestTransactionAPI:
    list_url = reverse("inventory:transaction-list")

    def test_list_transactions(self, authenticated_client):
        response = authenticated_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_purchase_transaction(self, authenticated_client, product):
        data = {
            "product": str(product.id),
            "transaction_type": "purchase",
            "quantity": 20,
            "reference": "PO-001",
        }
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["quantity"] == 20
        assert response.data["quantity_before"] == 50
        assert response.data["quantity_after"] == 70

        # Verify product quantity was updated
        product.refresh_from_db()
        assert product.quantity == 70

    def test_create_sale_transaction(self, authenticated_client, product):
        data = {
            "product": str(product.id),
            "transaction_type": "sale",
            "quantity": 10,
            "reference": "INV-001",
        }
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["quantity"] == -10  # Outbound = negative
        assert response.data["quantity_after"] == 40

        product.refresh_from_db()
        assert product.quantity == 40

    def test_insufficient_stock(self, authenticated_client, product):
        data = {
            "product": str(product.id),
            "transaction_type": "sale",
            "quantity": 999,
        }
        response = authenticated_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_transactions_are_immutable(self, authenticated_client, product, organization, owner_user):
        tx = InventoryTransaction.objects.create(
            organization=organization,
            product=product,
            performed_by=owner_user,
            transaction_type="purchase",
            quantity=10,
            quantity_before=50,
            quantity_after=60,
        )
        detail_url = reverse("inventory:transaction-detail", kwargs={"pk": tx.id})

        # PUT should not be allowed
        response = authenticated_client.put(detail_url, {"quantity": 999})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # DELETE should not be allowed
        response = authenticated_client.delete(detail_url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_viewer_cannot_create(self, viewer_client, product):
        data = {
            "product": str(product.id),
            "transaction_type": "purchase",
            "quantity": 5,
        }
        response = viewer_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tenant_isolation(self, other_org_client, product):
        """User from another org cannot create transaction for this org's product."""
        data = {
            "product": str(product.id),
            "transaction_type": "purchase",
            "quantity": 5,
        }
        response = other_org_client.post(self.list_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
