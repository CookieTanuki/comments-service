from django.urls import path

from apps.attachments.views import AttachmentCreateView

urlpatterns = [
    path("", AttachmentCreateView.as_view(), name="attachments-create"),
]
