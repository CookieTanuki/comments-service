import os

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from captcha.models import CaptchaStore

from .models import Comment
from apps.attachments.models import Attachment, validate_file
from .utils import sanitize_html, ALLOWED_TAGS
from .services.service import send_comment_event


User = get_user_model()


class RecursiveField(serializers.Serializer):

    def to_representation(self, value):
        serializer = CommentSerializer(value, context=self.context)
        return serializer.data


class CommentAttachmentSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "name", "url", "uploaded_at"]

    def get_name(self, obj) -> str:
        return os.path.basename(obj.file.name)

    def get_url(self, obj) -> str:
        if not obj.file:
            return ""

        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class CommentSerializer(serializers.ModelSerializer):
    attachments = CommentAttachmentSerializer(many=True, read_only=True)

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

    captcha_key = serializers.CharField(write_only=True, required=False)
    captcha_response = serializers.CharField(write_only=True, required=False)

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
            "updated_at",
            "is_edited",
            "is_deleted",
            "attachments",
            "uploaded_files",
            "remove_attachments",
            "captcha_key",
            "captcha_response",
            "children",
        ]

        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "user": {"read_only": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["text"] = "Deleted comment"

        return data

    def create(self, validated_data):
        files = validated_data.pop("uploaded_files", [])
        captcha_key = validated_data.pop("captcha_key", None)
        validated_data.pop("captcha_response", None)

        with transaction.atomic():
            comment = Comment.objects.create(**validated_data)

            for file in files:
                Attachment.objects.create(file=file, comment=comment)

            if captcha_key:
                CaptchaStore.objects.filter(hashkey=captcha_key).delete()

        send_comment_event({
            "type": "created",
            "id": comment.id,
            "text": comment.text,
        })

        return comment

    def update(self, instance, validated_data):
        if instance.is_deleted:
            raise serializers.ValidationError("Cannot edit deleted comment")

        files = validated_data.pop("uploaded_files", [])
        remove_ids = validated_data.pop("remove_attachments", [])
        validated_data.pop("captcha_key", None)
        validated_data.pop("captcha_response", None)
        validated_data.pop("email", None)
        validated_data.pop("parent", None)
        validated_data.pop("user", None)
        validated_data.pop("username", None)
        original_text = instance.text

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            if "text" in validated_data and validated_data["text"] != original_text:
                instance.is_edited = True

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

        send_comment_event({
            "type": "updated",
            "id": instance.id,
            "text": instance.text,
        })

        return instance

    def validate_uploaded_files(self, value):
        for file in value:
            validate_file(file)

        return value

    def validate_text(self, value):
        return sanitize_html(value, tags=ALLOWED_TAGS)

    def validate(self, attrs):
        request = self.context["request"]
        username = attrs.get("username")
        email = attrs.get("email")

        if username is not None:
            attrs["username"] = username.strip()

        if email is not None:
            attrs["email"] = email.strip()

        parent = attrs.get("parent")

        if parent and parent.is_deleted:
            raise serializers.ValidationError("Cannot reply to deleted comment")

        if not request.user.is_authenticated:
            if not attrs.get("username"):
                raise serializers.ValidationError({"username": "Username required"})

            if not attrs.get("email"):
                raise serializers.ValidationError({"email": "Email required"})

            if User.objects.filter(username__iexact=attrs["username"]).exists():
                raise serializers.ValidationError({
                    "username": "This username is already registered",
                })

            captcha_key = attrs.get("captcha_key")
            captcha_response = attrs.get("captcha_response")

            if not captcha_key:
                raise serializers.ValidationError({"captcha_key": "Captcha key required"})

            if not captcha_response:
                raise serializers.ValidationError({"captcha_response": "Captcha answer required"})

            captcha = CaptchaStore.objects.filter(
                hashkey=captcha_key,
                response=captcha_response.strip().lower(),
                expiration__gt=timezone.now(),
            ).first()
            if captcha is None:
                raise serializers.ValidationError({"captcha_response": "Invalid captcha"})

        return super().validate(attrs)
