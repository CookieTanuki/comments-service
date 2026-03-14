from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Comment

@receiver(post_save, sender=Comment)
def update_parent_replies_count(sender, instance, created, **kwargs):
    if created and instance.parent:
        parent = instance.parent
        parent.replies_count += 1
        parent.save(update_fields=["replies_count"])
