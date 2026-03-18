from rest_framework.generics import CreateAPIView

from .models import Attachment
from .serializers import AttachmentSerializer


class AttachmentCreateView(CreateAPIView):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
