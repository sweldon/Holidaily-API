from .models import Month
from .serializers import MonthSerializer, UserSerializer
from django.contrib.auth.models import User

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import generics, permissions


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "users": reverse("user-list", request=request, format=format),
            "months": reverse("month-list", request=request, format=format),
        }
    )


class MonthList(generics.ListCreateAPIView):
    queryset = Month.objects.all()
    serializer_class = MonthSerializer
    permission_classes = (permissions.IsAuthenticated,)


class MonthDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Month.objects.all()
    serializer_class = MonthSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
