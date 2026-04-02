from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"
    verbose_name = "Inventory Management"

    def ready(self):
        pass  # Register signals here if needed
