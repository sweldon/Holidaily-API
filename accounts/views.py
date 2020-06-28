from rest_framework.response import Response
from django.contrib.auth import authenticate
from api.models import UserProfile
from rest_framework import status as rest_status, generics
from django.contrib.auth.models import User
from api.constants import DISALLOWED_EMAILS
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six
from api.serializers import UserProfileSerializer
from api.disallowed_usernames import BAD_USERNAMES, BASIC_BAD_WORDS
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from holidaily.settings import (
    ENABLE_NEW_USER_ALERT,
    EMAIL_HOST_USER,
    EMAIL_HOST,
    VALIDATE_EMAIL,
)
from holidaily.utils import send_slack, sync_devices
from validate_email import validate_email


class UserLoginView(generics.GenericAPIView):
    def post(self, request):
        username = request.data.get("username", None)
        password = request.data.get("password", None)
        device_id = request.data.get("device_id", None)
        platform = request.data.get("platform", None)
        version = request.data.get("version", None)
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
                update_fields = ["logged_out"]
                # Re-enable notifications
                user_profile.logged_out = False
                if device_id and device_id != user_profile.device_id:
                    user_profile.device_id = device_id
                    update_fields.append("device_id")
                if platform and platform != user_profile.platform:
                    user_profile.platform = platform
                    update_fields.append("platform")
                if version and version != user_profile.version:
                    user_profile.version = version
                    update_fields.append("version")
                user_profile.save(update_fields=update_fields)
                if device_id and platform:
                    sync_devices(device_id, platform, user)
                serializer = UserProfileSerializer(
                    user_profile, context={"requesting_user": username}
                )
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
        device_id = request.data.get("device_id", None)
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
            if VALIDATE_EMAIL:
                email_is_valid = validate_email(
                    email_address=email,
                    check_regex=True,
                    check_mx=True,
                    from_address=EMAIL_HOST_USER,
                    helo_host=EMAIL_HOST,
                    smtp_timeout=10,
                    dns_timeout=10,
                    use_blacklist=True,
                    debug=False,
                )
                if not email_is_valid:
                    return Response(
                        {
                            "message": f"The email you provided is not valid. Please make sure there "
                            f"are no typos: {email}",
                            "status": rest_status.HTTP_400_BAD_REQUEST,
                        },
                    )

            # User profile will be created on first login
            user = User.objects.create_user(
                username=username, password=password, is_active=False, email=email
            )
            current_site = get_current_site(request)
            mail_subject = "Welcome to Holidaily!"
            activation_token = self.account_activation_token.make_token(user)
            html_message = render_to_string(
                "portal/activate.html",
                {
                    "user": user,
                    "domain": current_site.domain,
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": activation_token,
                },
            )
            activation_email = EmailMultiAlternatives(mail_subject, to=[email])
            activation_email.attach_alternative(html_message, "text/html")
            activation_email.send(fail_silently=False)
            UserProfile.objects.create(user=user, device_id=device_id)
            if ENABLE_NEW_USER_ALERT:
                send_slack(
                    f":alert: NEW USER ALERT :alert: *{username}* ({email})",
                    channel="hype",
                )
            return Response(
                {
                    "message": "OK",
                    "status": rest_status.HTTP_200_OK,
                    "token": activation_token,
                },
                status=rest_status.HTTP_200_OK,
            )
