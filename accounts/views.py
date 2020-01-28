from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from api.models import UserProfile
from rest_framework import status as rest_status, generics
from django.contrib.auth.models import User
from api.constants import DISALLOWED_EMAILS
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six

from api.serializers import UserSerializer


class UserLoginView(generics.GenericAPIView):
    def post(self, request):
        username = request.data.get("username", None)
        password = request.data.get("password", None)
        device_id = request.data.get("device_id", None)
        user = authenticate(username=username, password=password)

        if not device_id:
            return Response(
                {"message": "Could not register your device"},
                status=rest_status.HTTP_400_BAD_REQUEST,
            )

        if user:
            user_profile = UserProfile.objects.get_or_create(
                user=user, defaults={"device_id": device_id}
            )[0]
            active = user_profile.active
            if active:
                # Update device ID if necessary
                current_device_id = user_profile.device_id
                if device_id != current_device_id:
                    user_profile.device_id = device_id
                    user_profile.save()
                serializer = UserSerializer(user)
                results = {
                    "results": serializer.data,
                    "status": rest_status.HTTP_200_OK,
                }
                return Response(results)
            else:
                return Response(
                    {
                        "message": "You've been banned",
                        "status": rest_status.HTTP_401_UNAUTHORIZED,
                    },
                )
        else:
            return Response(
                {
                    "message": "Login failed, please try again",
                    "status": rest_status.HTTP_401_UNAUTHORIZED,
                },
            )


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk)
            + six.text_type(timestamp)
            + six.text_type(user.is_active)
        )


class UserRegisterView(APIView):
    account_activation_token = TokenGenerator()

    def post(self, request):
        username = request.data.get("username", None)
        password = request.data.get("password", None)
        email = request.data.get("email", None)
        existing_user = User.objects.filter(username=username).exists()
        existing_email = User.objects.filter(email=email).exists()
        if (
            not existing_email
            and not existing_user
            and email.split("@")[0] not in DISALLOWED_EMAILS
        ):
            # User profile will be created on first login
            user = User.objects.create_user(
                username=username, password=password, is_active=False, email=email
            )
            current_site = get_current_site(request)
            mail_subject = "Welcome to Holidaily!"
            message = render_to_string(
                "portal/activate.html",
                {
                    "user": user,
                    "domain": current_site.domain,
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": self.account_activation_token.make_token(user),
                },
            )
            activation_email = EmailMessage(mail_subject, message, to=[email])
            activation_email.send(fail_silently=False)
            return Response({"message": "OK"}, status=rest_status.HTTP_200_OK)
        else:
            return Response(
                {"message": "That name or email is not allowed."},
                status=rest_status.HTTP_400_BAD_REQUEST,
            )
