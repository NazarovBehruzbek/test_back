from django import forms
from django.contrib import admin
from django.utils import timezone

from app.common.validators import clean_optional_text, normalize_phone
from app.core.security import hash_password
from django_admin.vms.models import RefreshToken, StaffUser, Visit, Visitor

admin.site.site_header = "AqlliOlam — Django Admin"
admin.site.site_title = "AqlliOlam Admin"
admin.site.index_title = "Tashrifchilarni boshqarish tizimi"


class _StaffAdminAccessMixin:
    """Grant model access in Django Admin to authenticated active Admins and Super Admins."""

    def has_module_permission(self, request) -> bool:
        return bool(request.user.is_active and request.user.is_staff)

    def has_view_permission(self, request, obj=None) -> bool:
        return bool(request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request) -> bool:
        return bool(request.user.is_active and request.user.is_staff)

    def has_change_permission(self, request, obj=None) -> bool:
        return bool(request.user.is_active and request.user.is_staff)

    def has_delete_permission(self, request, obj=None) -> bool:
        return bool(request.user.is_active and request.user.is_staff)


class StaffUserAdminForm(forms.ModelForm):
    """Admin form exposing a plaintext password input hashed via Argon2id on save."""

    new_password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(render_value=False),
        label="Parol",
        help_text="Yangi xodim uchun majburiy. Tahrirlashda o'zgartirmasangiz bo'sh qoldiring.",
    )

    class Meta:
        model = StaffUser
        exclude = ("password_hash", "created_at", "updated_at")

    def clean_email(self) -> str:
        return str(self.cleaned_data["email"]).strip().lower()

    def clean_phone(self) -> str | None:
        raw = clean_optional_text(self.cleaned_data.get("phone"))
        if raw is None:
            return None
        return normalize_phone(raw)

    def clean(self):
        cleaned = super().clean()
        is_new = self.instance._state.adding
        if is_new and not cleaned.get("new_password"):
            self.add_error("new_password", "Yangi foydalanuvchi uchun parol kiritish shart.")
        return cleaned


@admin.register(StaffUser)
class StaffUserAdmin(_StaffAdminAccessMixin, admin.ModelAdmin):
    """Django Admin interface for system staff (`users` table)."""

    form = StaffUserAdminForm
    list_display = ("full_name", "email", "phone", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("full_name", "email", "phone")
    readonly_fields = ("id", "created_at", "updated_at")

    def has_change_permission(self, request, obj: StaffUser | None = None) -> bool:
        if not super().has_change_permission(request, obj):
            return False
        if obj is not None and not request.user.is_superuser:
            return obj.role == StaffUser.Role.OPERATOR
        return True

    def has_delete_permission(self, request, obj: StaffUser | None = None) -> bool:
        return bool(request.user.is_active and request.user.is_superuser)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "role" and not request.user.is_superuser:
            kwargs["choices"] = [(StaffUser.Role.OPERATOR, "Operator")]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def save_model(self, request, obj: StaffUser, form: StaffUserAdminForm, change: bool) -> None:
        if not request.user.is_superuser:
            obj.role = StaffUser.Role.OPERATOR
        raw_password = form.cleaned_data.get("new_password")
        if raw_password:
            obj.password_hash = hash_password(raw_password)
        super().save_model(request, obj, form, change)


@admin.register(Visitor)
class VisitorAdmin(_StaffAdminAccessMixin, admin.ModelAdmin):
    """Django Admin interface for building visitors (`visitors` table)."""

    list_display = (
        "full_name",
        "phone",
        "organization",
        "document_number",
        "deleted_at",
        "created_at",
    )
    list_filter = ("deleted_at",)
    search_fields = ("full_name", "phone", "organization", "document_number")
    readonly_fields = ("id", "created_at", "updated_at")
    actions = ("soft_delete_visitors", "restore_visitors")

    def save_model(self, request, obj: Visitor, form, change: bool) -> None:
        obj.full_name = obj.full_name.strip()
        obj.phone = normalize_phone(obj.phone)
        obj.document_number = clean_optional_text(obj.document_number)
        obj.organization = clean_optional_text(obj.organization)
        obj.notes = clean_optional_text(obj.notes)
        super().save_model(request, obj, form, change)

    @admin.action(description="Tanlangan tashrifchilarni yumshoq o'chirish (soft-delete)")
    def soft_delete_visitors(self, request, queryset) -> None:
        updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        self.message_user(request, f"{updated} ta tashrifchi arxivlandi.")

    @admin.action(description="Arxivlangan tashrifchilarni tiklash")
    def restore_visitors(self, request, queryset) -> None:
        updated = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(request, f"{updated} ta tashrifchi tiklandi.")


@admin.register(Visit)
class VisitAdmin(_StaffAdminAccessMixin, admin.ModelAdmin):
    """Django Admin interface for visitor check-ins and check-outs (`visits` table)."""

    list_display = (
        "visitor",
        "purpose",
        "host_name",
        "badge_number",
        "checked_in_at",
        "checked_out_at",
        "is_inside",
    )
    list_filter = ("checked_in_at", "checked_out_at")
    search_fields = (
        "visitor__full_name",
        "visitor__phone",
        "purpose",
        "host_name",
        "badge_number",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    actions = ("mark_checked_out",)

    @admin.display(boolean=True, description="Binoda")
    def is_inside(self, obj: Visit) -> bool:
        return obj.checked_out_at is None

    def save_model(self, request, obj: Visit, form, change: bool) -> None:
        obj.purpose = clean_optional_text(obj.purpose)
        obj.host_name = clean_optional_text(obj.host_name)
        obj.badge_number = clean_optional_text(obj.badge_number)
        obj.notes = clean_optional_text(obj.notes)
        super().save_model(request, obj, form, change)

    @admin.action(description="Tanlangan tashriflarni chiqish qayd etish (Check-out)")
    def mark_checked_out(self, request, queryset) -> None:
        updated = queryset.filter(checked_out_at__isnull=True).update(
            checked_out_at=timezone.now()
        )
        self.message_user(request, f"{updated} ta tashrif yakunlandi.")


@admin.register(RefreshToken)
class RefreshTokenAdmin(_StaffAdminAccessMixin, admin.ModelAdmin):
    """Django Admin interface for viewing and revoking JWT refresh tokens."""

    list_display = ("user", "expires_at", "revoked_at", "created_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__email", "user__full_name")
    readonly_fields = ("id", "user", "token_hash", "expires_at", "revoked_at", "created_at")
    actions = ("revoke_tokens",)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    @admin.action(description="Tanlangan sessiya tokenlarini bekor qilish")
    def revoke_tokens(self, request, queryset) -> None:
        updated = queryset.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
        self.message_user(request, f"{updated} ta sessiya tokeni bekor qilindi.")
