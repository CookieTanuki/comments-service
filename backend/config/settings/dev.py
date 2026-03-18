from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = ["rest_framework.authentication.SessionAuthentication"]

CACHES["default"]["LOCATION"] = "redis://127.0.0.1:6379/1"

USE_S3 = False

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
