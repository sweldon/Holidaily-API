from rest_framework import serializers
from .models import Month
from django.contrib.auth.models import User


class MonthSerializer(serializers.ModelSerializer):
    class Meta:
        model = Month
        fields = (
            "id",
            "name",
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")
