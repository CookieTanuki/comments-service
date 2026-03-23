import os

from .base import *

DEBUG = False

ALLOWED_HOSTS = [""]

USE_S3 = False

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                os.getenv(
                    "CHANNEL_LAYERS_REDIS_URL",
                    os.getenv("REDIS_URL", "redis://redis:6379/2"),
                )
            ],
        },
    }
}
