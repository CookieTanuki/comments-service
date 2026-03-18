from rest_framework import serializers
from .models import Comment
from apps.attachments.models import Attachment
from .utils import sanitize_html


class AttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attachment

        fields = ["id", "file"]


class RecursiveField(serializers.Serializer):

    def to_representation(self, value):
        serializer = CommentSerializer(value, context=self.context)
        return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    attachments = AttachmentSerializer(many=True)

    children = RecursiveField(many=True, read_only=True)

    class Meta:
        model = Comment

        fields = [
            "id",
            "user",
            "username",
            "email",
            "homepage",
            "parent",
            "text",
            "replies_count",
            "created_at",
            "attachments",
            "children",
        ]

    def validate_text(self, value):
        return sanitize_html(value)

    def validate(self, attrs):
        request = self.context["request"]

        if not request.user.is_authenticated:

            if not attrs.get("username"):
                raise serializers.ValidationError("Username required")

            if not attrs.get("email"):
                raise serializers.ValidationError("Email required")

        return attrs
