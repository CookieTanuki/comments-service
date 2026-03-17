from django.conf import settings
from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

User = settings.AUTH_USER_MODEL

class Comment(MPTTModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
    )

    username = models.CharField(max_length=50)

    email = models.EmailField()

    homepage = models.URLField(
        blank=True,
        null=True,
    )

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )

    text = models.TextField()

    replies_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    is_edited = models.BooleanField(default=False)

    class MPTTMeta:
        order_insertion_by = ["created_at"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.username} - {self.text[:30]}"
