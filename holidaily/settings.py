"""
Django settings for holidaily project.

Generated by 'django-admin startproject' using Django 2.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import slack

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "#$abpho2x@*2#i1ze_!r=8yl^lzud9v1gnz(o08t#8qg83zh4g"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False if os.environ["debug"] == "False" else True

ALLOWED_HOSTS = [
    "10.0.2.2",
    "localhost",
    "ec2-52-6-245-91.compute-1.amazonaws.com",
    "holidailyapp.com",
    "www.holidailyapp.com",
]

TEST_MODE = False if os.environ["debug"] == "False" else True

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "api",
    "rest_framework.authtoken",
    "accounts",
    "portal",
    "easyaudit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "easyaudit.middleware.easyaudit.EasyAuditMiddleware",
]

ROOT_URLCONF = "holidaily.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "holidaily.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ["db_name"],
        "USER": os.environ["db_user"],
        "PASSWORD": os.environ["db_pass"],
        "HOST": os.environ["db_host"],
        "PORT": "3306",
        "OPTIONS": {"charset": "utf8mb4"},
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en-us"

USE_I18N = True

USE_L10N = True

USE_TZ = False
TIME_ZONE = "America/New_York"


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = "/static/"

EMAIL_USE_TLS = True
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = "holidailyapp@gmail.com"
EMAIL_HOST_PASSWORD = os.environ["email_pass"]
EMAIL_PORT = 587
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(os.path.dirname(__file__), "../static")
STATICFILES_DIRS = (("base", os.path.join(STATIC_ROOT, "base").replace("\\", "/")),)

# Push notifications
APPCENTER_API_KEY = os.environ["appcenter_api"]
PUSH_ENDPOINT_ANDROID = (
    "https://api.appcenter.ms/v0.1/apps/steven.d.weldon-gmail.com/Holidaily-Android-Dev/"
    "push/notifications/"
)

PUSH_ENDPOINT_IOS = "https://api.appcenter.ms/v0.1/apps/steven.d.weldon-gmail.com/Holidaily-IOS/push/notifications"

SLACK_CLIENT = slack.WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# Supports second, minute, hour, day
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "50/minute"},
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

# Force HTTPS
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
