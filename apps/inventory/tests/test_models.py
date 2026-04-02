"""
Unit tests for inventory models — Category, Warehouse, Product, InventoryTransaction.
"""

import pytest
from decimal import Decimal

from apps.core.models import Organization
from apps.inventory.models import (
    Category,
    InventoryTransaction,
    Product,
    Warehouse,
)


@pytest.mark.django_db
class TestCategory:
    def test_create_category(self, organization):
        cat = Category.objects.create(
            organization=organization,
            name="Electronics",
            slug="electronics",
        )
        assert cat.name == "Electronics"
        assert cat.organization == organization

    def test_category_str(self, organization):
        cat = Category.objects.create(
            organization=organization,
            name="Electronics",
            slug="electronics",
        )
        assert str(cat) == "Electronics"

    def test_category_parent(self, organization):
        parent = Category.objects.create(
            organization=organization,
            name="Electronics",
            slug="electronics",
        )
        child = Category.objects.create(
            organization=organization,
            name="Laptops",
            slug="laptops",
            parent=parent,
        )
        assert child.parent == parent
        assert parent.children.count() == 1

    def test_unique_slug_per_organization(self, organization):
        Category.objects.create(
            organization=organization,
            name="Electronics",
            slug="electronics",
        )
        with pytest.raises(Exception):
            Category.objects.create(
                organization=organization,
                name="Electronics 2",
                slug="electronics",
            )

    def test_same_slug_different_orgs(self, organization, other_organization):
        Category.objects.create(
            organization=organization,
            name="Electronics",
            slug="electronics",
        )
        cat2 = Category.objects.create(
            organization=other_organization,
            name="Electronics",
            slug="electronics",
        )
        assert cat2.pk is not None  # Should succeed

    def test_tenant_manager(self, organization, other_organization):
        Category.objects.create(
            organization=organization, name="Cat A", slug="cat-a"
        )
        Category.objects.create(
            organization=other_organization, name="Cat B", slug="cat-b"
        )
        qs = Category.objects.for_organization(organization)
        assert qs.count() == 1
        assert qs.first().name == "Cat A"


@pytest.mark.django_db
class TestWarehouse:
    def test_create_warehouse(self, organization):
        wh = Warehouse.objects.create(
            organization=organization,
            name="Main Warehouse",
            code="WH-001",
            city="New York",
            country="US",
        )
        assert wh.name == "Main Warehouse"
        assert wh.is_active is True

    def test_warehouse_str(self, organization):
        wh = Warehouse.objects.create(
            organization=organization,
            name="Main",
            code="WH-001",
        )
        assert str(wh) == "Main (WH-001)"

    def test_unique_code_per_org(self, organization):
        Warehouse.objects.create(
            organization=organization, name="WH1", code="WH-001"
        )
        with pytest.raises(Exception):
            Warehouse.objects.create(
                organization=organization, name="WH2", code="WH-001"
            )


@pytest.mark.django_db
class TestProduct:
    @pytest.fixture
    def category(self, organization):
        return Category.objects.create(
            organization=organization, name="Electronics", slug="electronics"
        )

    @pytest.fixture
    def warehouse(self, organization):
        return Warehouse.objects.create(
            organization=organization, name="Main", code="WH-001"
        )

    def test_create_product(self, organization, category, warehouse):
        product = Product.objects.create(
            organization=organization,
            category=category,
            warehouse=warehouse,
            name="Laptop",
            sku="LAP-001",
            unit_price=Decimal("999.99"),
            cost_price=Decimal("750.00"),
            quantity=50,
        )
        assert product.name == "Laptop"
        assert product.sku == "LAP-001"
        assert product.quantity == 50

    def test_product_str(self, organization):
        product = Product.objects.create(
            organization=organization,
            name="Laptop",
            sku="LAP-001",
            unit_price=Decimal("999.99"),
        )
        assert str(product) == "Laptop [LAP-001]"

    def test_is_low_stock(self, organization):
        product = Product.objects.create(
            organization=organization,
            name="Widget",
            sku="WDG-001",
            unit_price=Decimal("10.00"),
            quantity=5,
            low_stock_threshold=10,
        )
        assert product.is_low_stock is True

    def test_not_low_stock(self, organization):
        product = Product.objects.create(
            organization=organization,
            name="Widget",
            sku="WDG-002",
            unit_price=Decimal("10.00"),
            quantity=50,
            low_stock_threshold=10,
        )
        assert product.is_low_stock is False

    def test_stock_value(self, organization):
        product = Product.objects.create(
            organization=organization,
            name="Widget",
            sku="WDG-003",
            unit_price=Decimal("10.00"),
            cost_price=Decimal("7.50"),
            quantity=100,
        )
        assert product.stock_value == Decimal("750.00")

    def test_unique_sku_per_org(self, organization):
        Product.objects.create(
            organization=organization,
            name="A",
            sku="SKU-001",
            unit_price=Decimal("10.00"),
        )
        with pytest.raises(Exception):
            Product.objects.create(
                organization=organization,
                name="B",
                sku="SKU-001",
                unit_price=Decimal("20.00"),
            )


@pytest.mark.django_db
class TestInventoryTransaction:
    @pytest.fixture
    def product(self, organization):
        return Product.objects.create(
            organization=organization,
            name="Widget",
            sku="WDG-TX",
            unit_price=Decimal("10.00"),
            quantity=100,
        )

    def test_create_transaction(self, organization, product, owner_user):
        tx = InventoryTransaction.objects.create(
            organization=organization,
            product=product,
            performed_by=owner_user,
            transaction_type=InventoryTransaction.TransactionType.PURCHASE,
            quantity=50,
            quantity_before=100,
            quantity_after=150,
        )
        assert tx.quantity == 50
        assert tx.quantity_before == 100
        assert tx.quantity_after == 150

    def test_transaction_str(self, organization, product, owner_user):
        tx = InventoryTransaction.objects.create(
            organization=organization,
            product=product,
            performed_by=owner_user,
            transaction_type=InventoryTransaction.TransactionType.SALE,
            quantity=-10,
            quantity_before=100,
            quantity_after=90,
        )
        assert "Sale" in str(tx)
        assert "-10" in str(tx)
