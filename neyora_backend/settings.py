"""
Django settings for neyora_backend project (Neyora — client-agnostic Notification /
Conversation / Calendar & Scheduling engine, per calendar-scheduling/UrbanNest_CalendarScheduling_Architecture.md).

ENV-VAR GOTCHA — READ BEFORE TOUCHING THIS FILE:
This project reads every environment-derived value through `python-decouple`'s
`config()`, NEVER through `os.environ`/`os.environ.get()`. The two are not
interchangeable: `python-decouple`'s own `.env` file support loads values into its
own config registry, it does NOT inject them into the real process environment, so
a later `os.environ.get("SOME_VAR")` call sees nothing even though `.env` has the
value. This exact bug shipped once already, in UrbanNest-Core-Backend's own seed
migration (`core/migrations/0009_seed_un_admin_superuser.py` reading
`os.environ.get('UN_ADMIN_PASSWORD', ...)`), silently falling back to a hardcoded
default password in production — see
`infrastructure/UrbanNest_AWS_Deployment_Running.md` §7 Phase 3 step 6. Any new
code in this project (management commands, data migrations, scripts) that needs a
config value must import `from decouple import config` and use that, never
`os.environ`.
"""

from pathlib import Path

from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# No hardcoded fallback on purpose — a missing SECRET_KEY should fail loudly at
# startup, not silently run on a well-known default.
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    # Neyora's own apps. Per ARCH_049/ARCH_052, every model here is client-agnostic
    # and Neyo-prefixed where it lives exclusively in this database — see each
    # app's own models.py for what it owns and which architecture-doc phase builds
    # it. All five below are scaffolded (empty, no models yet) as of Nov 7, 2026 —
    # see each app's models.py docstring before adding a model to the wrong one.
    "healthcheck",
    "core",            # Phase 0.5 (Neyora side) — NeyoClient, widget-token issuance
    "scheduling",       # Phase 1C — NeyoCalendar/NeyoEventType/NeyoCalendarEvent
                        # (named "scheduling", not "calendar" — see its models.py)
    "bookings",         # Phase 1D — NeyoBookingRequest/Availability/SchedulingPolicy
    "notifications",    # Phase 1A — NeyoNotification/NeyoReferenceValue
    "messaging",        # Phase 1B — NeyoConversation/NeyoMessage
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "neyora_backend.urls"

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

WSGI_APPLICATION = "neyora_backend.wsgi.application"


# Database
# ARCH_055 — Neyora's production database is confirmed PostgreSQL, Neyora's own
# database, separate from UrbanNest's (the shared EC2 instance already has a
# `neyora` OS user + `neyora_db`/`neyora_app` Postgres role provisioned and idle —
# see infrastructure/UrbanNest_AWS_Deployment_Running.md §6). This project always
# talks to Postgres, in every environment, including local dev — per the
# architecture doc's own §17 testing strategy, "SQLite tests are not evidence of
# correctness here" for anything concurrency-related (§9.2's booking-conflict
# locking), so there is no sqlite fallback to avoid developing against the wrong
# engine by default. Run a local Postgres (or point DB_HOST at the sandbox client
# on the shared instance) rather than reaching for sqlite.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="neyora_db"),
        "USER": config("DB_USER", default="neyora_app"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
# Required by `manage.py collectstatic` at deploy time — UrbanNest-Core-Backend's
# own settings.py was missing this and it had to be patched in during its first
# real deploy (infrastructure/UrbanNest_AWS_Deployment_Running.md §7 Phase 3 step 2).
# Included from the start here so Neyora's own deploy doesn't repeat that fix.
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework — every Neyora API endpoint (§13 of the architecture doc)
# is built as a DRF view. Phase 0.5's real client-API-key / short-lived-widget-
# token auth (ARCH_050, §20) is now built for real (core/authentication.py,
# core/tokens.py) rather than left unconfigured. Both classes are listed by
# default so most endpoints accept either credential per §13 ("Neyora's auth
# layer accepts either credential on its API"); core.views.WidgetTokenView
# deliberately overrides this with just the API-key class — see its own
# docstring for why ("never callable with a short-lived token itself").
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.NeyoClientApiKeyAuthentication",
        "core.authentication.NeyoWidgetTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# CORS — the embeddable widget (ARCH_050) calls this API directly from whatever
# origin a client embeds it on (UrbanNest's own frontend today, a different
# client's frontend later). No wildcard default; each client's embedding
# origin(s) must be added explicitly once known.
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())


# Email
# ARCH_053 — Phase 1E email delivery lives inside Neyora itself, never handed off
# to a client's Interface Layer. Provider choice (SES/Postmark/SendGrid) is a
# Phase 1E implementation decision; console backend is a safe placeholder until
# then so nothing crashes calling send_mail() in dev.
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
