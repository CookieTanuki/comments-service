from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

dev_cache_url = os.getenv("DEV_CACHE_URL")

if dev_cache_url:
    CACHES["default"]["LOCATION"] = dev_cache_url
else:
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "comments-service-dev",
    }

USE_S3 = False

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
