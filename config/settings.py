"""
Django settings for the Campus Marketplace project.
"""

from pathlib import Path

# The folder that holds manage.py
BASE_DIR = Path(__file__).resolve().parent.parent

# Test-only key for your own computer. We replace it with a secret one on Day 7.
SECRET_KEY = "django-insecure-dev-key-only-for-testing-change-me-on-day-7"

# True = helpful error pages while you build. Must be False on a real website.
DEBUG = True

ALLOWED_HOSTS = []


# The guest list of rooms (apps)
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "listings",
    "messaging",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "messaging.context_processors.unread_count",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database (a single file called db.sqlite3)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password rules
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Language and time
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Uploaded photos
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Login and logout
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "listings:home"
LOGOUT_REDIRECT_URL = "listings:home"
