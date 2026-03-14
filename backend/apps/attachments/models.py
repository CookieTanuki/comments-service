import os

from django.db import models
from rest_framework.exceptions import ValidationError
from PIL import Image


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
ALLOWED_TEXT_EXTENSIONS = {".txt"}

MAX_TEXT_SIZE = 100 * 1024


def validate_file(file):
    ext = os.path.splitext(file.name)[1].lower()

    if ext not in ALLOWED_IMAGE_EXTENSIONS + ALLOWED_TEXT_EXTENSIONS:
        raise ValidationError("Unsupported file type")

    if ext in ALLOWED_TEXT_EXTENSIONS and file.size > MAX_TEXT_SIZE:
        raise ValidationError("Text file too large (max 100kb)")


class Attachment(models.Model):
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="attachments/",
        validators=[validate_file],)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        ext = os.path.splitext(self.file.name)[1].lower()

        if ext in ALLOWED_IMAGE_EXTENSIONS:
            self.resize_image()

    def resize_image(self):
        image = Image.open(self.file.path)

        max_width = 320
        max_height = 240

        image.thumbnail((max_width, max_height))

        image.save(self.file.path)

    def __str__(self):
        return f"Attachment {self.id}"
