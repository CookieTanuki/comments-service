from django.conf import settings
from django.core.cache import cache

from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListCreateAPIView, CreateAPIView, get_object_or_404, DestroyAPIView, \
    RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Comment
from .serializers import CommentSerializer
from core.pagination import CommentPagination

from .utils import sanitize_html, ALLOWED_TAGS
from .services.cache import get_comments_cache_key, invalidate_comments_cache


class CommentListView(ListCreateAPIView):

    serializer_class = CommentSerializer

    pagination_class = CommentPagination

    filter_backends = [OrderingFilter]

    parser_classes = [MultiPartParser, FormParser]

    ordering_fields = [
        "username",
        "email",
        "created_at"
    ]

    ordering = ["-created_at"]

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

    def list(self, request, *args, **kwargs):

        cache_key = get_comments_cache_key(request)

        cached_response = cache.get(cache_key)

        if cached_response:
            #print("CACHE HIT")
            return Response(cached_response, status=status.HTTP_200_OK)

        #print("CACHE MISS")

        response = super().list(request, *args, **kwargs)

        cache.set(cache_key, response.data, timeout=settings.COMMENTS_CACHE_TIMEOUT)

        return response

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

        invalidate_comments_cache()


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

        invalidate_comments_cache()


class CommentPreviewView(APIView):

    def post(self, request):

        text = request.data.get("text", "")

        cleaned = sanitize_html(text, tags=ALLOWED_TAGS)

        return Response(
            {"preview": cleaned},
            status=status.HTTP_200_OK,
        )


class CommentUpdateView(RetrieveUpdateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)


class CommentDeleteView(DestroyAPIView):
    queryset = Comment.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)
