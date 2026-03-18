from captcha.fields import CaptchaField
from rest_framework import serializers
from .models import Comment
from apps.attachments.models import Attachment
from .utils import sanitize_html, ALLOWED_TAGS


class AttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attachment

        fields = ["id", "file"]


class RecursiveField(serializers.Serializer):

    def to_representation(self, value):
        serializer = CommentSerializer(value, context=self.context)
        return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    attachments = AttachmentSerializer(many=True, required=False)

    children = RecursiveField(many=True, read_only=True)

    captcha = CaptchaField(required=False)

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

        extra_kwargs = {
            "captcha": {"write_only": True},
        }

    def validate_text(self, value):
        return sanitize_html(value, tags=ALLOWED_TAGS)

    def validate(self, attrs):
        request = self.context["request"]

        if not request.user.is_authenticated:

            if not attrs.get("username"):
                raise serializers.ValidationError("Username required")

            if not attrs.get("email"):
                raise serializers.ValidationError("Email required")

            if not attrs.get("captcha"):
                raise serializers.ValidationError("Captcha required")

        return attrs
