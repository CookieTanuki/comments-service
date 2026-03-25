import tempfile
from unittest.mock import patch
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from captcha.models import CaptchaStore
from rest_framework.test import APIClient

from apps.attachments.models import Attachment
from apps.comments.models import Comment
from apps.comments.services.cache import get_comments_cache_key, invalidate_comments_cache


class CommentFlowsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.guest_client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="uploadtester",
            email="uploadtester@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.request_factory = RequestFactory()

        self.temp_media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.temp_media_dir.name,
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                }
            },
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.temp_media_dir.cleanup()

    def _uploaded_file(self, filename, content_type):
        backend_dir = Path(__file__).resolve().parents[3]
        return SimpleUploadedFile(
            filename,
            (backend_dir / filename).read_bytes(),
            content_type=content_type,
        )

    def _captcha_payload(self):
        key = CaptchaStore.generate_key()
        captcha = CaptchaStore.objects.get(hashkey=key)
        return {
            "captcha_key": key,
            "captcha_response": captcha.response,
        }

    def test_authenticated_user_can_create_comment_with_files_in_one_request(self):
        text_file = self._uploaded_file("test.txt", "text/plain")
        image_file = self._uploaded_file("testimage.png", "image/png")

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
        self.assertEqual(response.data["attachments"][0]["name"], "test.txt")
        self.assertIn("/media/attachments/", response.data["attachments"][0]["url"])

        comment = Comment.objects.get(pk=response.data["id"])
        attachments = Attachment.objects.filter(comment=comment).order_by("id")

        self.assertEqual(attachments.count(), 2)
        self.assertTrue(attachments[0].file.name.endswith(".txt"))
        self.assertTrue(attachments[1].file.name.endswith(".png"))

    def test_authenticated_user_can_create_comment_without_attachments_using_json(self):
        response = self.client.post(
            reverse("comments:list"),
            {
                "text": "plain comment",
                "username": "stale-guest",
                "email": "stale-guest@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], self.user.username)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_anonymous_user_can_fetch_captcha_and_create_comment(self):
        captcha_response = self.guest_client.get(reverse("comments:comment-captcha"))
        self.assertEqual(captcha_response.status_code, 200)
        self.assertIn("/captcha/image/", captcha_response.data["image_url"])

        captcha = CaptchaStore.objects.get(hashkey=captcha_response.data["key"])
        create_response = self.guest_client.post(
            reverse("comments:list"),
            {
                "text": "anonymous comment",
                "username": "guest-author",
                "email": "guest@example.com",
                "captcha_key": captcha.hashkey,
                "captcha_response": captcha.response,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["username"], "guest-author")
        self.assertEqual(create_response.data["email"], "guest@example.com")

    def test_anonymous_user_cannot_use_registered_username(self):
        get_user_model().objects.create_user(
            username="reserved-author",
            email="reserved-author@example.com",
            password="testpass123",
        )
        captcha = CaptchaStore.objects.get(hashkey=self.guest_client.get(
            reverse("comments:comment-captcha")
        ).data["key"])

        response = self.guest_client.post(
            reverse("comments:list"),
            {
                "text": "anonymous comment",
                "username": "Reserved-Author",
                "email": "guest@example.com",
                "captcha_key": captcha.hashkey,
                "captcha_response": captcha.response,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["username"][0], "This username is already registered")

    def test_authenticated_user_can_create_reply_without_attachments_using_json(self):
        parent = Comment.objects.create(
            user=self.user,
            username=self.user.username,
            email=self.user.email,
            text="parent comment",
        )

        response = self.client.post(
            reverse("comments:comment-reply", kwargs={"pk": parent.pk}),
            {
                "text": "reply comment",
                "username": "stale-guest",
                "email": "stale-guest@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        reply = Comment.objects.get(pk=response.data["id"])
        self.assertEqual(reply.parent_id, parent.pk)
        self.assertEqual(reply.username, self.user.username)
        self.assertEqual(reply.email, self.user.email)

    def test_authenticated_user_can_create_reply_with_files_in_one_request(self):
        parent = Comment.objects.create(
            user=self.user,
            username=self.user.username,
            email=self.user.email,
            text="parent comment",
        )
        text_file = self._uploaded_file("test.txt", "text/plain")
        image_file = self._uploaded_file("testimage.png", "image/png")

        response = self.client.post(
            reverse("comments:comment-reply", kwargs={"pk": parent.pk}),
            {
                "text": "reply with files",
                "uploaded_files": [text_file, image_file],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        reply = Comment.objects.get(pk=response.data["id"])
        attachments = Attachment.objects.filter(comment=reply).order_by("id")

        self.assertEqual(reply.parent_id, parent.pk)
        self.assertEqual(attachments.count(), 2)

    def test_authenticated_user_can_update_comment_text_and_attachments(self):
        comment = Comment.objects.create(
            user=self.user,
            username=self.user.username,
            email=self.user.email,
            text="before update",
        )
        old_text_file = Attachment.objects.create(
            comment=comment,
            file=self._uploaded_file("test.txt", "text/plain"),
        )
        Attachment.objects.create(
            comment=comment,
            file=self._uploaded_file("testimage.png", "image/png"),
        )

        response = self.client.patch(
            reverse("comments:comment-update", kwargs={"pk": comment.pk}),
            {
                "text": "after update",
                "username": "stale-guest",
                "email": "stale-guest@example.com",
                "remove_attachments": [old_text_file.pk],
                "uploaded_files": [self._uploaded_file("test.txt", "text/plain")],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        attachments = Attachment.objects.filter(comment=comment).order_by("id")

        self.assertEqual(comment.text, "after update")
        self.assertTrue(comment.is_edited)
        self.assertEqual(comment.username, self.user.username)
        self.assertEqual(comment.email, self.user.email)
        self.assertEqual(attachments.count(), 2)
        self.assertFalse(attachments.filter(pk=old_text_file.pk).exists())

    def test_soft_delete_keeps_comment_and_removes_attachments(self):
        comment = Comment.objects.create(
            user=self.user,
            username=self.user.username,
            email=self.user.email,
            text="comment to delete",
        )
        Attachment.objects.create(
            comment=comment,
            file=self._uploaded_file("test.txt", "text/plain"),
        )

        response = self.client.delete(
            reverse("comments:comment-delete", kwargs={"pk": comment.pk}),
        )

        self.assertEqual(response.status_code, 204)
        comment.refresh_from_db()

        self.assertTrue(comment.is_deleted)
        self.assertEqual(comment.text, "Deleted comment")
        self.assertEqual(comment.attachments.count(), 0)

    def test_cannot_reply_to_deleted_comment(self):
        parent = Comment.objects.create(
            user=self.user,
            username=self.user.username,
            email=self.user.email,
            text="parent comment",
            is_deleted=True,
        )

        response = self.client.post(
            reverse("comments:comment-reply", kwargs={"pk": parent.pk}),
            {"text": "reply should fail"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Comment.objects.filter(parent=parent).count(), 0)

    def test_comments_cache_key_changes_after_invalidation(self):
        request = self.request_factory.get("/comments/?page=1")

        first_key = get_comments_cache_key(request)
        invalidate_comments_cache()
        second_key = get_comments_cache_key(request)

        self.assertNotEqual(first_key, second_key)

    def test_comment_list_still_works_when_cache_backend_fails(self):
        Comment.objects.create(
            user=self.user,
            username=self.user.username,
            email=self.user.email,
            text="cached comment",
        )

        with patch("apps.comments.services.cache.cache.get", side_effect=RuntimeError("cache down")):
            with patch("apps.comments.services.cache.cache.set", side_effect=RuntimeError("cache down")):
                response = self.client.get(reverse("comments:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["text"], "cached comment")

    def test_standalone_attachment_create_endpoint_is_removed(self):
        response = self.client.post("/attachments/", {}, format="multipart")

        self.assertEqual(response.status_code, 404)
