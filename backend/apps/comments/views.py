from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListCreateAPIView, CreateAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Comment
from .serializers import CommentSerializer
from backend.core.pagination import CommentPagination

from .utils import sanitize_html

class CommentListView(ListCreateAPIView):

    serializer_class = CommentSerializer

    pagination_class = CommentPagination

    filter_backends = [OrderingFilter]

    ordering_fields = [
        "username",
        "email",
        "created_at"
    ]

    def get_queryset(self):

        return (
            Comment.objects
            .filter(parent=None)
            .select_related("user")
            .prefetch_related(
                "attachments",
                "children__attachments",
            )
        )

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_authenticated:
            serializer.save(
                user=user,
                username=serializer.validated_data.get("username", user.username),
                email=serializer.validated_data.get("email", user.email),
            )
        else:
            serializer.save(user=None)


class CommentReplyView(CreateAPIView):

    serializer_class = CommentSerializer

    def perform_create(self, serializer):

        parent_id = self.kwargs.get("pk")

        parent = get_object_or_404(Comment, pk=parent_id)

        user = self.request.user

        if user.is_authenticated:
            serializer.save(parent=parent, user=user)

        else:
            serializer.save(parent=parent)


class CommentPreviewView(APIView):

    def post(self, request):

        text = request.data.get("text", "")

        allowed_tags = ["a", "i", "code", "strong"]

        cleaned = sanitize_html(text)

        return Response(
            {"preview": cleaned},
            status=status.HTTP_200_OK,
        )
