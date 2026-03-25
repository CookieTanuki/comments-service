import os

from .base import *

DEBUG = False

ALLOWED_HOSTS = get_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = get_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = get_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = get_bool("CSRF_COOKIE_SECURE", False)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = get_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = get_bool("SECURE_HSTS_PRELOAD", False)

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
