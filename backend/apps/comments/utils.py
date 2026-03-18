import bleach


ALLOWED_TAGS = ["a", "i", "code", "strong"]


def sanitize_html(text: str) -> str:
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        strip=True,
    )
