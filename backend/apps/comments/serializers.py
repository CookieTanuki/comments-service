from captcha.fields import CaptchaField
from rest_framework import serializers
from .models import Comment
from apps.attachments.models import Attachment
from .utils import sanitize_html, ALLOWED_TAGS


class RecursiveField(serializers.Serializer):

    def to_representation(self, value):
        serializer = CommentSerializer(value, context=self.context)
        return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    attachments = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Attachment.objects.all(),
        required=False
    )

    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
    )

    replies_count = serializers.IntegerField(read_only=True)

    children = RecursiveField(many=True, read_only=True)

    captcha = CaptchaField(required=False)

    class Meta:
        model = Comment

        fields = [
            "id",
            "user",
            "username",
            "email",
            "parent",
            "text",
            "replies_count",
            "created_at",
            "attachments",
            "uploaded_files",
            "children",
        ]

        extra_kwargs = {
            "captcha": {"write_only": True},
        }

    def create(self, validated_data):
        request = self.context["request"]

        files = validated_data.pop("uploaded_files", [])

        attachments = validated_data.pop("attachments", [])

        comment = Comment.objects.create(**validated_data)

        for file in files:
            Attachment.objects.create(
                file=file,
                comment=comment,
            )

        for attachment in attachments:
            attachment.comment = comment
            attachment.save()

        return comment

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
