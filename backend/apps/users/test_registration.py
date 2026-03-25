from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_user_can_register(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newauthor",
                "email": "newauthor@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], "newauthor")
        self.assertEqual(response.data["email"], "newauthor@example.com")
        self.assertFalse("password" in response.data)
        self.assertTrue(User.objects.filter(username="newauthor").exists())

    def test_registration_rejects_duplicate_username_and_email_case_insensitively(self):
        User.objects.create_user(
            username="ExistingUser",
            email="existing@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "existinguser",
                "email": "EXISTING@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["username"][0], "This username is already taken")
        self.assertEqual(response.data["email"][0], "This email is already taken")

    def test_registration_requires_matching_passwords(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newauthor",
                "email": "newauthor@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass124!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["password_confirm"][0], "Passwords do not match")
