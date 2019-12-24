from rest_framework import serializers
from .models import Holiday
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class HolidaySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    votes = serializers.IntegerField()
    blurb = serializers.CharField()
    image = serializers.CharField()
    date = serializers.DateField()

    class Meta:
        model = Holiday
        fields = ("id", "name", "description", "votes", "blurb", "image", "date")
