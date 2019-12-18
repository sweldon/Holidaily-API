from rest_framework.test import APITestCase
from api import factories
from rest_framework import status as rest_status
from api.constants import NO_DEVICE_ERROR


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
