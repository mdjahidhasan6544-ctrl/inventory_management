"""
Inventory Models — Products, Categories, Warehouses, Transactions.

Every model carries an organization FK and is scoped through
TenantQuerySet / TenantManager to enforce data isolation.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import Organization, TimeStampedModel


# =============================================================================
# Tenant-Aware Manager
# =============================================================================


class TenantQuerySet(models.QuerySet):
    """Queryset that filters by organization automatically."""

    def for_organization(self, organization):
        return self.filter(organization=organization)


class TenantManager(models.Manager):
    """Manager that returns TenantQuerySet."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_organization(self, organization):
        return self.get_queryset().for_organization(organization)


# =============================================================================
# Category
# =============================================================================


class Category(TimeStampedModel):
    """
    Product category scoped to an organization.

    Supports one level of nesting via optional `parent` FK
    for hierarchical categorization (e.g. Electronics > Laptops).
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, db_index=True)
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    objects = TenantManager()

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        unique_together = [("organization", "slug")]
        indexes = [
            models.Index(fields=["organization", "name"]),
        ]

    def __str__(self):
        return self.name


# =============================================================================
# Warehouse
# =============================================================================


class Warehouse(TimeStampedModel):
    """
    Physical or logical warehouse belonging to an organization.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="warehouses",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, db_index=True)
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, default="US")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)

    objects = TenantManager()

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
        unique_together = [("organization", "code")]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


# =============================================================================
# Product
# =============================================================================


class Product(TimeStampedModel):
    """
    A product within the organization's inventory.

    The `quantity` field is denormalized for fast reads; it is kept
    in sync via InventoryTransaction signals or service-layer logic.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    name = models.CharField(max_length=255)
    sku = models.CharField("SKU", max_length=50, db_index=True)
    barcode = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    quantity = models.IntegerField(
        default=0,
        help_text="Current stock level (denormalized for fast reads).",
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert when quantity drops below this.",
    )

    unit = models.CharField(
        max_length=20,
        choices=[
            ("pcs", "Pieces"),
            ("kg", "Kilograms"),
            ("lbs", "Pounds"),
            ("lt", "Litres"),
            ("m", "Metres"),
            ("box", "Boxes"),
        ],
        default="pcs",
    )
    is_active = models.BooleanField(default=True)

    objects = TenantManager()

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Product"
        verbose_name_plural = "Products"
        unique_together = [("organization", "sku")]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "category"]),
            models.Index(fields=["organization", "warehouse"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.sku}]"

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    @property
    def stock_value(self):
        return self.quantity * self.cost_price


# =============================================================================
# Inventory Transaction
# =============================================================================


class InventoryTransaction(TimeStampedModel):
    """
    Immutable ledger of stock changes.

    Every stock movement (purchase, sale, transfer, adjustment, return)
    creates a new InventoryTransaction rather than mutating Product.quantity
    directly. The Product.quantity field is updated as a side effect.
    """

    class TransactionType(models.TextChoices):
        PURCHASE = "purchase", "Purchase (Stock In)"
        SALE = "sale", "Sale (Stock Out)"
        TRANSFER_IN = "transfer_in", "Transfer In"
        TRANSFER_OUT = "transfer_out", "Transfer Out"
        ADJUSTMENT = "adjustment", "Adjustment"
        RETURN = "return", "Return"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=15,
        choices=TransactionType.choices,
    )
    quantity = models.IntegerField(
        help_text="Positive = stock in, negative = stock out.",
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="PO number, invoice number, or other reference.",
    )
    notes = models.TextField(blank=True, default="")

    # Snapshot for audit trail
    quantity_before = models.IntegerField(
        help_text="Product quantity before this transaction.",
    )
    quantity_after = models.IntegerField(
        help_text="Product quantity after this transaction.",
    )

    objects = TenantManager()

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"
        indexes = [
            models.Index(fields=["organization", "product"]),
            models.Index(fields=["organization", "transaction_type"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        direction = "+" if self.quantity > 0 else ""
        return (
            f"{self.get_transaction_type_display()} | "
            f"{self.product.name} {direction}{self.quantity}"
        )
