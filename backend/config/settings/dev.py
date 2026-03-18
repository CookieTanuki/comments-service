from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

CACHES["default"]["LOCATION"] = "redis://127.0.0.1:6379/1"
