from rest_framework import serializers

from holidaily.utils import normalize_time
from .models import (
    Holiday,
    Comment,
    UserProfile,
    UserNotifications,
    UserHolidayVotes,
    UserCommentVotes,
)
from django.contrib.auth.models import User
from api.constants import (
    UPVOTE,
    DOWNVOTE,
    UPVOTE_ONLY,
    DOWNVOTE_ONLY,
    NEWS_NOTIFICATION,
    COMMENT_NOTIFICATION,
)
from django.utils import timezone
import humanize


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    premium = serializers.BooleanField()

    def get_username(self, obj):
        return obj.user.username

    class Meta:
        model = UserProfile
        fields = ('holiday_submissions', 'approved_holidays', 'confetti',
                  'num_comments', 'username', 'premium')

class UserSerializer(serializers.ModelSerializer):
    is_premium = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    confetti = serializers.SerializerMethodField()

    def get_is_premium(self, obj):
        return UserProfile.objects.get(user=obj).premium

    def get_is_active(self, obj):
        return UserProfile.objects.get(user=obj).active

    def get_confetti(self, obj):
        return UserProfile.objects.get(user=obj).confetti

    class Meta:
        model = User
        fields = ("id", "username", "is_premium", "is_active", "confetti")


class CommentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    content = serializers.CharField()
    holiday_id = serializers.ReadOnlyField(source="holiday.pk")
    user = serializers.ReadOnlyField(source="user.username")
    timestamp = serializers.DateTimeField()
    votes = serializers.IntegerField()
    parent = serializers.ReadOnlyField(source="self.pk")
    time_since = serializers.SerializerMethodField()
    vote_status = serializers.SerializerMethodField()

    def get_time_since(self, obj):
        time_ago = humanize.naturaltime(timezone.now() - obj.timestamp)
        return normalize_time(time_ago, "precise")

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
            "user",
            "timestamp",
            "votes",
            "parent",
            "time_since",
            "vote_status",
        )


class HolidaySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    votes = serializers.IntegerField()
    push = serializers.CharField()
    image = serializers.CharField()
    date = serializers.DateField()
    num_comments = serializers.IntegerField()
    time_since = serializers.SerializerMethodField()
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    celebrating = serializers.SerializerMethodField()
    active = serializers.BooleanField()
    blurb = serializers.CharField()

    def get_time_since(self, obj):
        time_ago = humanize.naturaltime(timezone.now().date() - obj.date)
        return normalize_time(time_ago, "relative")

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
            "push",
            "image",
            "date",
            "num_comments",
            "time_since",
            "creator",
            "celebrating",
            "active",
            "blurb"
        )


class UserNotificationsSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="user.username")
    notification_id = serializers.IntegerField()
    notification_type = serializers.SerializerMethodField()
    read = serializers.BooleanField()
    content = serializers.CharField()
    timestamp = serializers.DateTimeField()
    title = serializers.CharField()
    time_since = serializers.SerializerMethodField()

    def get_notification_type(self, obj):
        if obj.notification_type == NEWS_NOTIFICATION:
            return "News"
        elif obj.notification_type == COMMENT_NOTIFICATION:
            return "Comment"

    def get_time_since(self, obj):
        time_ago = humanize.naturaltime(timezone.now() - obj.timestamp)
        return normalize_time(time_ago, "precise")

    class Meta:
        model = UserNotifications
        fields = (
            "author",
            "notification_id",
            "notification_type",
            "read",
            "content",
            "timestamp",
            "title",
            "time_since",
        )
