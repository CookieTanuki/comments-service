import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

COMMENTS_CACHE_VERSION_KEY = "comments:list:version"


def get_comments_cache_key(request):
    try:
        version = int(cache.get(COMMENTS_CACHE_VERSION_KEY, 1))
    except Exception:
        logger.exception("Failed to read comments cache version")
        version = 1

    return f"comments:list:v{version}:{request.get_full_path()}"


def get_comments_list_cache(cache_key):
    try:
        return cache.get(cache_key)
    except Exception:
        logger.exception("Failed to read comments list cache")
        return None


def set_comments_list_cache(cache_key, payload, timeout):
    try:
        cache.set(cache_key, payload, timeout=timeout)
    except Exception:
        logger.exception("Failed to write comments list cache")


def invalidate_comments_cache():
    try:
        version = int(cache.get(COMMENTS_CACHE_VERSION_KEY, 1))
        cache.set(COMMENTS_CACHE_VERSION_KEY, version + 1, None)
    except Exception:
        logger.exception("Failed to invalidate comments cache")
