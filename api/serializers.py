from rest_framework import serializers
from .models import Holiday, Comment, UserProfile, UserNotifications
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    is_premium = serializers.SerializerMethodField()

    def get_is_premium(self, obj):
        return UserProfile.objects.get(user=obj).premium

    class Meta:
        model = User
        fields = ("id", "username", "is_premium")


class CommentSerializer(serializers.ModelSerializer):
    content = serializers.CharField()
    holiday_pk = serializers.ReadOnlyField(source="holiday.pk")
    user_pk = serializers.ReadOnlyField(source="user.pk")
    timestamp = serializers.DateTimeField()
    votes = serializers.IntegerField()
    parent = serializers.ReadOnlyField(source="self")
    time_since = serializers.CharField()

    class Meta:
        model = Comment
        fields = (
            "content",
            "holiday_pk",
            "user_pk",
            "timestamp",
            "votes",
            "parent",
            "time_since",
        )


class HolidaySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    votes = serializers.IntegerField()
    blurb = serializers.CharField()
    image = serializers.CharField()
    date = serializers.DateField()
    comments = CommentSerializer(many=True)
    num_comments = serializers.IntegerField()
    time_since = serializers.CharField()
    creator = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Holiday
        fields = (
            "id",
            "name",
            "description",
            "votes",
            "blurb",
            "image",
            "date",
            "comments",
            "num_comments",
            "time_since",
            "creator",
        )


class UserNotificationsSerializer(serializers.ModelSerializer):
    user_pk = serializers.ReadOnlyField(source="user.pk")
    notification_id = serializers.IntegerField()
    notification_type = serializers.IntegerField()
    read = serializers.BooleanField()
    content = serializers.CharField()
    timestamp = serializers.DateTimeField()
    title = serializers.CharField()

    class Meta:
        model = UserNotifications
        fields = (
            "user_pk",
            "notification_id",
            "notification_type",
            "read",
            "content",
            "timestamp",
            "title",
        )
