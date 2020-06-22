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
    CLOUDFRONT_DOMAIN,
)
from django.utils import timezone
import humanize


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    premium = serializers.BooleanField()
    profile_image = serializers.SerializerMethodField()
    last_online = serializers.SerializerMethodField()

    def get_username(self, obj):
        return obj.user.username

    def get_profile_image(self, obj):
        requesting_user = self.context.get("requesting_user", None)
        # Don't censor user's own avatar
        if not obj.profile_image:
            return None
        elif requesting_user:
            if (
                requesting_user.lower() == obj.user.username.lower()
                or obj.avatar_approved
            ):
                return f"{CLOUDFRONT_DOMAIN}/{obj.profile_image}"
        elif obj.avatar_approved:
            return f"{CLOUDFRONT_DOMAIN}/{obj.profile_image}"
        else:
            return None

    def get_last_online(self, obj):
        if obj.last_launched:
            time_ago = humanize.naturaltime(timezone.now() - obj.last_launched)
            return normalize_time(time_ago, "precise")
        else:
            return "a while ago"

    class Meta:
        model = UserProfile
        fields = (
            "holiday_submissions",
            "approved_holidays",
            "confetti",
            "num_comments",
            "username",
            "premium",
            "profile_image",
            "last_online",
        )


class UserSerializer(serializers.ModelSerializer):
    is_premium = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    confetti = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    approved_holidays = serializers.SerializerMethodField()
    last_online = serializers.SerializerMethodField()
    num_comments = serializers.SerializerMethodField()

    def get_is_premium(self, obj):
        return UserProfile.objects.get(user=obj).premium

    def get_is_active(self, obj):
        return UserProfile.objects.get(user=obj).active

    def get_confetti(self, obj):
        return UserProfile.objects.get(user=obj).confetti

    def get_approved_holidays(self, obj):
        return UserProfile.objects.get(user=obj).approved_holidays

    def get_num_comments(self, obj):
        return UserProfile.objects.get(user=obj).num_comments

    def get_last_online(self, obj):
        profile = UserProfile.objects.get(user=obj)
        if profile.last_launched:
            time_ago = humanize.naturaltime(timezone.now() - profile.last_launched)
            return normalize_time(time_ago, "precise")
        else:
            return "a while ago"

    def get_profile_image(self, obj):
        profile = UserProfile.objects.get(user=obj)
        if profile.profile_image:
            return f"{CLOUDFRONT_DOMAIN}/{profile.profile_image}"
        else:
            return None

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "is_premium",
            "is_active",
            "confetti",
            "profile_image",
            "approved_holidays",
            "last_online",
            "num_comments",
            "email",
        )


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
    deleted = serializers.BooleanField()

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
            "deleted",
        )


class HolidaySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    votes = serializers.IntegerField()
    push = serializers.CharField()
    image = serializers.SerializerMethodField()
    date = serializers.DateField()
    num_comments = serializers.IntegerField()
    time_since = serializers.SerializerMethodField()
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    celebrating = serializers.SerializerMethodField()
    active = serializers.BooleanField()
    blurb = serializers.CharField()

    def get_image(self, obj):
        return f"{CLOUDFRONT_DOMAIN}/{obj.image_name}"

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
            "blurb",
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
    icon = serializers.SerializerMethodField()

    def get_notification_type(self, obj):
        if obj.notification_type == NEWS_NOTIFICATION:
            return "News"
        elif obj.notification_type == COMMENT_NOTIFICATION:
            return "Comment"

    def get_time_since(self, obj):
        time_ago = humanize.naturaltime(timezone.now() - obj.timestamp)
        return normalize_time(time_ago, "precise")

    def get_icon(self, obj):
        profile = UserProfile.objects.filter(user=obj.user).first()
        icon = (
            f"{CLOUDFRONT_DOMAIN}/{profile.profile_image}"
            if profile and profile.avatar_approved
            else None
        )
        return icon

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
            "icon",
        )
