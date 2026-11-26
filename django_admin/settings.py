from pathlib import Path
from urllib.parse import unquote, urlparse

from app.core.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
_app_settings = get_settings()
_parsed_db = urlparse(_app_settings.database_url_str)

SECRET_KEY = _app_settings.SECRET_KEY
DEBUG = _app_settings.DEBUG
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_admin.vms.apps.VmsAdminConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "django_admin.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "django_admin.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _parsed_db.path.lstrip("/"),
        "USER": unquote(_parsed_db.username or ""),
        "PASSWORD": unquote(_parsed_db.password or ""),
        "HOST": _parsed_db.hostname or "localhost",
        "PORT": str(_parsed_db.port or 5432),
    }
}

AUTHENTICATION_BACKENDS = [
    "django_admin.vms.auth_backend.StaffEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LANGUAGE_CODE = "uz"
TIME_ZONE = _app_settings.TIMEZONE
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
