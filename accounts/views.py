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
from api.serializers import UserProfileSerializer
from api.disallowed_usernames import BAD_USERNAMES, BASIC_BAD_WORDS
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


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

                # Re-enable notifications
                user_profile.logged_out = False
                user_profile.save()

                # Update device ID if necessary
                current_device_id = user_profile.device_id
                if device_id != current_device_id:
                    user_profile.device_id = device_id
                    user_profile.save()
                serializer = UserProfileSerializer(user_profile)
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


class UserRegisterView(generics.GenericAPIView):
    account_activation_token = TokenGenerator()

    def post(self, request):
        username = request.data.get("username", None)
        password = request.data.get("password", None)
        email = request.data.get("email", None)
        existing_user = User.objects.filter(username=username).exists()
        existing_email = User.objects.filter(email=email).exists()

        try:
            validate_password(password)
        except ValidationError as e:
            reasons = " ".join(e)
            error_message = f"Your password isn't strong enough: {reasons}"
            return Response(
                {"message": error_message, "status": rest_status.HTTP_400_BAD_REQUEST},
            )

        # Initial bad word check
        for word in BASIC_BAD_WORDS:
            if word in username.lower():
                return Response(
                    {
                        "message": "That username or email is taken, or not allowed.",
                        "status": rest_status.HTTP_400_BAD_REQUEST,
                    },
                )

        if (
            existing_email
            or existing_user
            or email.split("@")[0] in DISALLOWED_EMAILS
            or "holidaily" in username.lower()
            or "holidaily" in email.lower()
            or "dvnt" in username.lower()
            or username in BAD_USERNAMES
        ):
            return Response(
                {
                    "message": "That username or email is taken, or not allowed.",
                    "status": rest_status.HTTP_400_BAD_REQUEST,
                },
            )
        else:
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
            return Response(
                {"message": "OK", "status": rest_status.HTTP_200_OK},
                status=rest_status.HTTP_200_OK,
            )
