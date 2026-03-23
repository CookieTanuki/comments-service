import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.attachments.models import Attachment
from apps.comments.models import Comment


class CommentCreateWithUploadsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="uploadtester",
            email="uploadtester@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

        self.temp_media_dir = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media_dir.name)
        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        self.temp_media_dir.cleanup()

    def test_authenticated_user_can_create_comment_with_files_in_one_request(self):
        backend_dir = Path(__file__).resolve().parents[3]
        text_file = SimpleUploadedFile(
            "test.txt",
            (backend_dir / "test.txt").read_bytes(),
            content_type="text/plain",
        )
        image_file = SimpleUploadedFile(
            "testimage.png",
            (backend_dir / "testimage.png").read_bytes(),
            content_type="image/png",
        )

        response = self.client.post(
            reverse("comments:list"),
            {
                "text": "comment with files",
                "uploaded_files": [text_file, image_file],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], self.user.username)
        self.assertEqual(response.data["email"], self.user.email)

        comment = Comment.objects.get(pk=response.data["id"])
        attachments = Attachment.objects.filter(comment=comment).order_by("id")

        self.assertEqual(attachments.count(), 2)
        self.assertTrue(attachments[0].file.name.endswith(".txt"))
        self.assertTrue(attachments[1].file.name.endswith(".png"))
