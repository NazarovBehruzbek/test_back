from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from app.core.security import verify_dummy_password, verify_password
from django_admin.vms.models import StaffUser

_ALLOWED_ROLES = {StaffUser.Role.SUPER_ADMIN, StaffUser.Role.ADMIN}


class StaffEmailBackend(BaseBackend):
    """Authenticate Django Admin logins against the FastAPI `users` table (Argon2id)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        email = str(username).strip().lower()
        staff = StaffUser.objects.filter(email__iexact=email).first()
        if staff is None:
            verify_dummy_password(password)
            return None

        if not verify_password(password, staff.password_hash):
            return None

        django_user_model = get_user_model()
        allowed = staff.is_active and staff.role in _ALLOWED_ROLES
        if not allowed:
            django_user_model.objects.filter(username=email).update(
                is_active=False,
                is_staff=False,
            )
            return None

        django_user, created = django_user_model.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": staff.full_name[:150],
                "is_staff": True,
                "is_superuser": staff.role == StaffUser.Role.SUPER_ADMIN,
                "is_active": True,
            },
        )
        if created:
            django_user.set_unusable_password()
            django_user.save()
        else:
            changed = False
            expected_super = staff.role == StaffUser.Role.SUPER_ADMIN
            if (
                django_user.email != email
                or django_user.first_name != staff.full_name[:150]
                or not django_user.is_staff
                or not django_user.is_active
                or django_user.is_superuser != expected_super
            ):
                django_user.email = email
                django_user.first_name = staff.full_name[:150]
                django_user.is_staff = True
                django_user.is_active = True
                django_user.is_superuser = expected_super
                changed = True
            if changed:
                django_user.save()

        return django_user

    def get_user(self, user_id):
        django_user_model = get_user_model()
        try:
            return django_user_model.objects.get(pk=user_id)
        except django_user_model.DoesNotExist:
            return None
