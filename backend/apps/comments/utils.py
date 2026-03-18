import bleach


ALLOWED_TAGS = ["a", "i", "code", "strong"]


def sanitize_html(text: str, tags: list = None) -> str:
    if tags is None:
        tags = ALLOWED_TAGS
    return bleach.clean(
        text,
        tags=tags,
        strip=True,
    )
