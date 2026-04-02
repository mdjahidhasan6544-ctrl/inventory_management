"""
Integration tests — cross-cutting concerns across multiple components.

Tests multi-tenancy isolation, transaction atomicity, and full workflow scenarios.
"""

import pytest
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from apps.core.models import Organization, User
from apps.inventory.models import (
    Category,
    InventoryTransaction,
    Product,
    Warehouse,
)


@pytest.mark.django_db
@pytest.mark.integration
class TestMultiTenantIsolation:
    """
    Verify that Organization A's data is completely invisible
    to Organization B's users across all endpoints.
    """

    @pytest.fixture
    def setup_two_tenants(self, organization, other_organization, owner_user, other_org_user):
        # Org A data
        cat_a = Category.objects.create(
            organization=organization, name="Cat A", slug="cat-a"
        )
        wh_a = Warehouse.objects.create(
            organization=organization, name="WH A", code="WH-A"
        )
        prod_a = Product.objects.create(
            organization=organization,
            name="Product A",
            sku="PROD-A",
            unit_price=Decimal("100.00"),
            quantity=50,
            category=cat_a,
            warehouse=wh_a,
        )

        # Org B data
        cat_b = Category.objects.create(
            organization=other_organization, name="Cat B", slug="cat-b"
        )
        wh_b = Warehouse.objects.create(
            organization=other_organization, name="WH B", code="WH-B"
        )
        prod_b = Product.objects.create(
            organization=other_organization,
            name="Product B",
            sku="PROD-B",
            unit_price=Decimal("200.00"),
            quantity=30,
            category=cat_b,
            warehouse=wh_b,
        )

        return {
            "org_a": {"cat": cat_a, "wh": wh_a, "prod": prod_a},
            "org_b": {"cat": cat_b, "wh": wh_b, "prod": prod_b},
        }

    def test_category_isolation(self, authenticated_client, other_org_client, setup_two_tenants):
        url = reverse("inventory:category-list")

        resp_a = authenticated_client.get(url)
        resp_b = other_org_client.get(url)

        names_a = [c["name"] for c in resp_a.data["results"]]
        names_b = [c["name"] for c in resp_b.data["results"]]

        assert "Cat A" in names_a
        assert "Cat B" not in names_a
        assert "Cat B" in names_b
        assert "Cat A" not in names_b

    def test_product_isolation(self, authenticated_client, other_org_client, setup_two_tenants):
        url = reverse("inventory:product-list")

        resp_a = authenticated_client.get(url)
        resp_b = other_org_client.get(url)

        skus_a = [p["sku"] for p in resp_a.data["results"]]
        skus_b = [p["sku"] for p in resp_b.data["results"]]

        assert "PROD-A" in skus_a
        assert "PROD-B" not in skus_a
        assert "PROD-B" in skus_b
        assert "PROD-A" not in skus_b

    def test_warehouse_isolation(self, authenticated_client, other_org_client, setup_two_tenants):
        url = reverse("inventory:warehouse-list")

        resp_a = authenticated_client.get(url)
        resp_b = other_org_client.get(url)

        codes_a = [w["code"] for w in resp_a.data["results"]]
        codes_b = [w["code"] for w in resp_b.data["results"]]

        assert "WH-A" in codes_a
        assert "WH-B" not in codes_a

    def test_cross_tenant_transaction_blocked(self, other_org_client, setup_two_tenants):
        """Org B user should not be able to create a transaction for Org A's product."""
        prod_a = setup_two_tenants["org_a"]["prod"]
        url = reverse("inventory:transaction-list")
        data = {
            "product": str(prod_a.id),
            "transaction_type": "purchase",
            "quantity": 10,
        }
        response = other_org_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestFullPurchaseWorkflow:
    """End-to-end test: register → create product → purchase → verify stock."""

    def test_complete_workflow(self, api_client):
        # 1. Register a new organization
        register_url = reverse("auth:register")
        reg_data = {
            "org_name": "Workflow Corp",
            "org_slug": "workflow-corp",
            "username": "wfuser",
            "email": "wf@wfcorp.com",
            "password": "WorkflowP@ss1",
        }
        reg_resp = api_client.post(register_url, reg_data)
        assert reg_resp.status_code == status.HTTP_201_CREATED

        token = reg_resp.data["tokens"]["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 2. Create a category
        cat_resp = api_client.post(
            reverse("inventory:category-list"),
            {"name": "Hardware", "slug": "hardware"},
        )
        assert cat_resp.status_code == status.HTTP_201_CREATED
        cat_id = cat_resp.data["id"]

        # 3. Create a warehouse
        wh_resp = api_client.post(
            reverse("inventory:warehouse-list"),
            {"name": "Central", "code": "WH-C"},
        )
        assert wh_resp.status_code == status.HTTP_201_CREATED
        wh_id = wh_resp.data["id"]

        # 4. Create a product
        prod_resp = api_client.post(
            reverse("inventory:product-list"),
            {
                "name": "Server Rack",
                "sku": "RACK-001",
                "unit_price": "2500.00",
                "cost_price": "1800.00",
                "category": cat_id,
                "warehouse": wh_id,
            },
        )
        assert prod_resp.status_code == status.HTTP_201_CREATED
        prod_id = prod_resp.data["id"]
        assert prod_resp.data["quantity"] == 0

        # 5. Purchase — add stock
        tx_resp = api_client.post(
            reverse("inventory:transaction-list"),
            {
                "product": prod_id,
                "transaction_type": "purchase",
                "quantity": 25,
                "reference": "PO-WF-001",
            },
        )
        assert tx_resp.status_code == status.HTTP_201_CREATED
        assert tx_resp.data["quantity_after"] == 25

        # 6. Verify product quantity
        prod_detail = api_client.get(
            reverse("inventory:product-detail", kwargs={"pk": prod_id})
        )
        assert prod_detail.data["quantity"] == 25

        # 7. Sale — reduce stock
        sale_resp = api_client.post(
            reverse("inventory:transaction-list"),
            {
                "product": prod_id,
                "transaction_type": "sale",
                "quantity": 5,
                "reference": "INV-WF-001",
            },
        )
        assert sale_resp.status_code == status.HTTP_201_CREATED
        assert sale_resp.data["quantity_after"] == 20

        # 8. Verify updated quantity
        prod_detail = api_client.get(
            reverse("inventory:product-detail", kwargs={"pk": prod_id})
        )
        assert prod_detail.data["quantity"] == 20


@pytest.mark.django_db
@pytest.mark.integration
class TestRBACEnforcement:
    """Verify role-based access across all inventory endpoints."""

    @pytest.fixture
    def product(self, organization):
        return Product.objects.create(
            organization=organization,
            name="RBAC Test Product",
            sku="RBAC-001",
            unit_price=Decimal("10.00"),
            quantity=100,
        )

    def test_manager_can_create_product(self, manager_client):
        data = {"name": "Manager Prod", "sku": "MGR-001", "unit_price": "50.00"}
        response = manager_client.post(reverse("inventory:product-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_viewer_cannot_create_product(self, viewer_client):
        data = {"name": "Viewer Prod", "sku": "VIEW-001", "unit_price": "50.00"}
        response = viewer_client.post(reverse("inventory:product-list"), data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_can_read_product(self, viewer_client, product):
        url = reverse("inventory:product-detail", kwargs={"pk": product.id})
        response = viewer_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_manager_can_create_transaction(self, manager_client, product):
        data = {
            "product": str(product.id),
            "transaction_type": "purchase",
            "quantity": 10,
        }
        response = manager_client.post(reverse("inventory:transaction-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_viewer_cannot_create_transaction(self, viewer_client, product):
        data = {
            "product": str(product.id),
            "transaction_type": "purchase",
            "quantity": 10,
        }
        response = viewer_client.post(reverse("inventory:transaction-list"), data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_blocked(self, api_client):
        response = api_client.get(reverse("inventory:product-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
