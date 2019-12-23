from rest_framework.test import APITestCase
from api import factories
from rest_framework import status as rest_status
from api.constants import NO_DEVICE_ERROR
from django.contrib.auth.models import User
from django.core import mail


class UserLoginTest(APITestCase):
    def setUp(self):
        self.username = "test_user"
        self.password = "password123"
        self.device_id = "deviceId12456"
        self.user = factories.UserFactory(
            username=self.username, password=self.password
        )
        self.user_profile = factories.UserProfile(
            user=self.user, device_id=self.device_id
        )
        self.user_profile.save()
        self.login_url = "/accounts/login/"

    def test_login_with_device_id(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.username,
                "password": self.password,
                "device_id": self.device_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)

    def test_login_no_device_id(self):
        response = self.client.post(
            self.login_url,
            {"username": self.username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, rest_status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], NO_DEVICE_ERROR)


# TODO make this it's own test file
class UserRegisterTest(APITestCase):
    def setUp(self):
        self.username = "test_user"
        self.password = "password123"
        self.email = "test@test.com"
        self.register_url = "/accounts/register/"
        self.login_url = "/accounts/login/"
        self.device_id = "deviceId12456"

    def test_register_user(self):
        response = self.client.post(
            self.register_url,
            {
                "username": self.username,
                "password": self.password,
                "email": self.email,
            },
            format="json",
        )
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
        # User followed activation link
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Welcome to Holidaily!")
        self.assertEqual(mail.outbox[0].to, [self.email])
        response = self.client.post(
            self.login_url,
            {
                "username": self.username,
                "password": self.password,
                "device_id": self.device_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, rest_status.HTTP_401_UNAUTHORIZED)

        # Simulate user following activation link
        user = User.objects.get(username=self.username)
        user.is_active = True
        user.save()
        response = self.client.post(
            self.login_url,
            {
                "username": self.username,
                "password": self.password,
                "device_id": self.device_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, rest_status.HTTP_200_OK)
