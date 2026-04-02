from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core (Users & Organizations)"

    def ready(self):
        pass  # Register signals here if needed
