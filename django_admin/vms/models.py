import uuid

from django.db import models
from django.utils import timezone


class StaffUser(models.Model):
    """Unmanaged Django model mapped to the PostgreSQL `users` table."""

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        OPERATOR = "operator", "Operator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=150, verbose_name="To'liq ism")
    email = models.EmailField(max_length=255, verbose_name="Email")
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefon",
    )
    password_hash = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OPERATOR,
        verbose_name="Rol",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        managed = False
        db_table = "users"
        ordering = ("-created_at",)
        verbose_name = "Xodim"
        verbose_name_plural = "Xodimlar"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.role})"


class Visitor(models.Model):
    """Unmanaged Django model mapped to the PostgreSQL `visitors` table."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=150, verbose_name="F.I.Sh.")
    phone = models.CharField(max_length=20, verbose_name="Telefon")
    document_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Hujjat raqami",
    )
    organization = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Tashkilot",
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    created_by = models.ForeignKey(
        StaffUser,
        on_delete=models.SET_NULL,
        db_column="created_by",
        blank=True,
        null=True,
        related_name="created_visitors",
        verbose_name="Kiritgan xodim",
    )
    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="O'chirilgan vaqt",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        managed = False
        db_table = "visitors"
        ordering = ("-created_at",)
        verbose_name = "Tashrifchi"
        verbose_name_plural = "Tashrifchilar"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"


class Visit(models.Model):
    """Unmanaged Django model mapped to the PostgreSQL `visits` table."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.RESTRICT,
        db_column="visitor_id",
        related_name="visits",
        verbose_name="Tashrifchi",
    )
    checked_in_by = models.ForeignKey(
        StaffUser,
        on_delete=models.SET_NULL,
        db_column="checked_in_by",
        blank=True,
        null=True,
        related_name="checked_in_visits",
        verbose_name="Kiritgan operator",
    )
    checked_out_by = models.ForeignKey(
        StaffUser,
        on_delete=models.SET_NULL,
        db_column="checked_out_by",
        blank=True,
        null=True,
        related_name="checked_out_visits",
        verbose_name="Chiqargan operator",
    )
    purpose = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Maqsad",
    )
    host_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Qabul qiluvchi",
    )
    badge_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Beyjik",
    )
    checked_in_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Kelgan vaqti",
    )
    checked_out_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Ketgan vaqti",
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        managed = False
        db_table = "visits"
        ordering = ("-checked_in_at",)
        verbose_name = "Tashrif"
        verbose_name_plural = "Tashriflar"

    def __str__(self) -> str:
        return f"{self.visitor.full_name} — {self.checked_in_at:%Y-%m-%d %H:%M}"


class RefreshToken(models.Model):
    """Unmanaged Django model mapped to the PostgreSQL `refresh_tokens` table."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        StaffUser,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="refresh_tokens",
        verbose_name="Xodim",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(verbose_name="Tugash vaqti")
    revoked_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Bekor qilingan",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan")

    class Meta:
        managed = False
        db_table = "refresh_tokens"
        ordering = ("-created_at",)
        verbose_name = "Sessiya tokeni"
        verbose_name_plural = "Sessiya tokenlari"

    def __str__(self) -> str:
        return f"{self.user.email} ({self.created_at:%Y-%m-%d %H:%M})"
