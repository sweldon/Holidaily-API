from django.db.models import Sum
from rest_framework import serializers
from .models import (
    Holiday,
    Comment,
    UserProfile,
    UserNotifications,
    UserHolidayVotes,
    UserCommentVotes,
)
from django.contrib.auth.models import User
from api.constants import UPVOTE, DOWNVOTE, UPVOTE_ONLY, DOWNVOTE_ONLY


class UserSerializer(serializers.ModelSerializer):
    is_premium = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    confetti = serializers.SerializerMethodField()

    def get_is_premium(self, obj):
        return UserProfile.objects.get(user=obj).premium

    def get_is_active(self, obj):
        return UserProfile.objects.get(user=obj).active

    def get_confetti(self, obj):
        user_profile = UserProfile.objects.get(user=obj)
        points = user_profile.rewards
        comment_votes = Comment.objects.filter(user=obj).aggregate(Sum('votes'))
        if comment_votes["votes__sum"]:
            comment_points = comment_votes["votes__sum"] if comment_votes["votes__sum"] > 0 else 0
        else:
            comment_points = 0
        points += comment_points
        return points

    class Meta:
        model = User
        fields = ("id", "username", "is_premium", "is_active", "confetti")


# class RecursiveField(serializers.Serializer):
#     def to_representation(self, value):
#         serializer = self.parent.parent.__class__(value, context=self.context)
#         print(serializer.data)
#         return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    content = serializers.CharField()
    holiday_id = serializers.ReadOnlyField(source="holiday.pk")
    user_pk = serializers.ReadOnlyField(source="user.pk")
    timestamp = serializers.DateTimeField()
    votes = serializers.IntegerField()
    parent = serializers.IntegerField()
    time_since = serializers.CharField()
    vote_status = serializers.SerializerMethodField()
    # replies = RecursiveField(many=True)

    def get_vote_status(self, obj):
        username = self.context.get("username", None)
        if username:
            if UserCommentVotes.objects.filter(
                user__username=username, comment=obj, choice__in=UPVOTE_ONLY
            ).exists():
                return UPVOTE
            elif UserCommentVotes.objects.filter(
                user__username=username, comment=obj, choice__in=DOWNVOTE_ONLY
            ).exists():
                return DOWNVOTE
            else:
                return None
        else:
            return None

    class Meta:
        model = Comment
        fields = (
            "id",
            "content",
            "holiday_id",
            "user_pk",
            "timestamp",
            "votes",
            "parent",
            "time_since",
            "vote_status",
            # "replies"
        )


class HolidaySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    votes = serializers.IntegerField()
    blurb = serializers.CharField()
    image = serializers.CharField()
    date = serializers.DateField()
    num_comments = serializers.IntegerField()
    time_since = serializers.CharField()
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    celebrating = serializers.SerializerMethodField()

    def get_celebrating(self, obj):
        username = self.context.get("username", None)
        if username:
            celebrating = UserHolidayVotes.objects.filter(
                user__username=username, holiday=obj, choice__in=UPVOTE_ONLY
            ).exists()
            return celebrating
        else:
            return False

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
            "num_comments",
            "time_since",
            "creator",
            "celebrating",
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
