from rest_framework import serializers
from .models import Comment
from backend.apps.attachments.models import Attachment


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
            "replies",
            "created_at",
            "attachments",
            "children",
        ]
