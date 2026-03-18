from django.core.cache import cache


def get_comments_cache_key(request):
    return f"comments:list:v1:{request.get_full_path()}"

def invalidate_comments_cache():
    try:
        keys = cache.keys("comments:list:*")
        if keys:
            cache.delete_many(keys)
    except Exception:
        pass
