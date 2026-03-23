from captcha.fields import CaptchaField
from django.db import transaction
from django.template.defaulttags import comment
from rest_framework import serializers
from .models import Comment
from apps.attachments.models import Attachment
from .utils import sanitize_html, ALLOWED_TAGS
from .services.service import send_comment_event


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

    remove_attachments = serializers.ListField(
        child=serializers.IntegerField(),
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
            "remove_attachments",
            "children",
        ]

        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "captcha": {"write_only": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["text"] = "Deleted comment"

        return data

    def create(self, validated_data):
        files = validated_data.pop("uploaded_files", [])

        validated_data.pop("attachments", None)

        with transaction.atomic():
            comment = Comment.objects.create(**validated_data)

            if files:
                attachments = [
                    Attachment(file=file, comment=comment)
                    for file in files
                ]

                Attachment.objects.bulk_create(attachments)

        send_comment_event({
            "type": "created",
            "id": comment.id,
            "text": comment.text,
        })

        return comment

    def update(self, instance, validated_data):
        files = validated_data.pop("uploaded_files", [])

        remove_ids = validated_data.pop("remove_attachments", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if remove_ids:
            Attachment.objects.filter(
                id__in=remove_ids,
                comment=instance,
                comment__user=self.context["request"].user,
            ).delete()

        for file in files:
            Attachment.objects.create(
                file=file,
                comment=instance,
            )

        if instance.is_deleted:
            raise serializers.ValidationError("Cannot edit deleted comment")

        send_comment_event({
            "type": "updated",
            "id": instance.id,
            "text": instance.text,
        })

        return super().update(instance, validated_data)

    def validate_text(self, value):
        return sanitize_html(value, tags=ALLOWED_TAGS)

    def validate(self, attrs):
        request = self.context["request"]

        parent = attrs.get("parent")

        if parent and parent.is_deleted:
            raise serializers.ValidationError("Cannot reply to deleted comment")

        if not request.user.is_authenticated:

            if not attrs.get("username"):
                raise serializers.ValidationError("Username required")

            if not attrs.get("email"):
                raise serializers.ValidationError("Email required")

            if not attrs.get("captcha"):
                raise serializers.ValidationError("Captcha required")

        return super().validate(attrs)
