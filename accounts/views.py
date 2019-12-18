from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from api.models import UserProfile
from rest_framework import status as rest_status


class UserLoginView(APIView):
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
                return Response({"message": "OK"}, status=rest_status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "You've been banned"},
                    status=rest_status.HTTP_401_UNAUTHORIZED,
                )
        else:
            return Response(
                {"message": "Login failed, please try again"},
                status=rest_status.HTTP_401_UNAUTHORIZED,
            )
