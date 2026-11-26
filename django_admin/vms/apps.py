from django.apps import AppConfig


class VmsAdminConfig(AppConfig):
    """Django app configuration for AqlliOlam VMS tables."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_admin.vms"
    verbose_name = "AqlliOlam — Tashriflar boshqaruvi"
