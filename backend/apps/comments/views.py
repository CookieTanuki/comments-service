from django.conf import settings
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer

from rest_framework import status, serializers
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListCreateAPIView, CreateAPIView, get_object_or_404, DestroyAPIView, \
    RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from .models import Comment
from .serializers import CommentSerializer
from core.pagination import CommentPagination
from .services.service import send_comment_event

from .utils import sanitize_html, ALLOWED_TAGS
from .services.cache import (
    get_comments_cache_key,
    get_comments_list_cache,
    invalidate_comments_cache,
    set_comments_list_cache,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Comments"],
        summary="List top-level comments",
        description="Return paginated top-level comments with nested replies and attachments.",
    ),
    post=extend_schema(
        tags=["Comments"],
        summary="Create a top-level comment",
        description=(
            "Create a new top-level comment. Guests must provide username, email, and captcha. "
            "Authenticated users inherit username and email from their account."
        ),
    ),
)
class CommentListView(ListCreateAPIView):

    serializer_class = CommentSerializer

    pagination_class = CommentPagination

    filter_backends = [OrderingFilter]

    parser_classes = [JSONParser, MultiPartParser, FormParser]

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

        cached_response = get_comments_list_cache(cache_key)

        if cached_response:
            #print("CACHE HIT")
            return Response(cached_response, status=status.HTTP_200_OK)

        #print("CACHE MISS")

        response = super().list(request, *args, **kwargs)

        set_comments_list_cache(
            cache_key,
            response.data,
            timeout=settings.COMMENTS_CACHE_TIMEOUT,
        )

        return response

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_authenticated:
            serializer.save(
                user=user,
                username=user.username,
                email=user.email,
            )
        else:
            serializer.save(user=None)

        invalidate_comments_cache()


@extend_schema_view(
    post=extend_schema(
        tags=["Comments"],
        summary="Create a reply",
        description="Create a reply for an existing comment.",
    ),
)
class CommentReplyView(CreateAPIView):

    serializer_class = CommentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def perform_create(self, serializer):

        parent_id = self.kwargs.get("pk")

        parent = get_object_or_404(Comment, pk=parent_id)
        if parent.is_deleted:
            raise serializers.ValidationError("Cannot reply to deleted comment")

        user = self.request.user

        if user.is_authenticated:
            serializer.save(
                parent=parent,
                user=user,
                username=user.username,
                email=user.email,
            )

        else:
            serializer.save(parent=parent)

        invalidate_comments_cache()


class CommentPreviewView(APIView):

    @extend_schema(
        tags=["Comments"],
        summary="Preview sanitized comment HTML",
        request=inline_serializer(
            name="CommentPreviewRequest",
            fields={
                "text": serializers.CharField(),
            },
        ),
        responses=inline_serializer(
            name="CommentPreviewResponse",
            fields={
                "preview": serializers.CharField(),
            },
        ),
    )
    def post(self, request):

        text = request.data.get("text", "")

        cleaned = sanitize_html(text, tags=ALLOWED_TAGS)

        return Response(
            {"preview": cleaned},
            status=status.HTTP_200_OK,
        )


class CommentCaptchaView(APIView):

    @extend_schema(
        tags=["Comments"],
        summary="Get captcha challenge",
        responses=inline_serializer(
            name="CommentCaptchaResponse",
            fields={
                "key": serializers.CharField(),
                "image_url": serializers.URLField(),
            },
        ),
    )
    def get(self, request):
        key = CaptchaStore.generate_key()

        return Response(
            {
                "key": key,
                "image_url": request.build_absolute_uri(captcha_image_url(key)),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Comments"],
        summary="Retrieve own comment",
        description="Retrieve a comment owned by the authenticated user.",
    ),
    patch=extend_schema(
        tags=["Comments"],
        summary="Update own comment",
        description="Update comment text and attachment set for a comment owned by the authenticated user.",
    ),
    put=extend_schema(
        tags=["Comments"],
        summary="Replace own comment",
        description="Replace a comment owned by the authenticated user.",
    ),
)
class CommentUpdateView(RetrieveUpdateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        invalidate_comments_cache()


@extend_schema_view(
    delete=extend_schema(
        tags=["Comments"],
        summary="Soft delete own comment",
        description="Soft delete a comment owned by the authenticated user and remove its attachments.",
        request=None,
        responses={204: None},
    ),
)
class CommentDeleteView(DestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.text = "Deleted comment"
        instance.save(update_fields=["is_deleted", "text"])
        instance.attachments.all().delete()
        invalidate_comments_cache()

        send_comment_event({
            "type": "deleted",
            "id": instance.id,
        })
