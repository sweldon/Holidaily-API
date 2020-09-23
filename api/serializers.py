from datetime import timedelta

from factory.django import get_model
from rest_framework import serializers

from holidaily.utils import normalize_time
from .models import (
    Holiday,
    Comment,
    UserProfile,
    UserNotifications,
    UserHolidayVotes,
    UserCommentVotes,
    Post,
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
    CONFETTI_COOLDOWN_MINUTES,
    POST_NOTIFICATION,
    LIKE_NOTIFICATION,
)
from django.utils import timezone
import humanize
from logging import getLogger

logger = getLogger("holidaily")


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    premium = serializers.BooleanField()
    profile_image = serializers.SerializerMethodField()
    last_online = serializers.SerializerMethodField()
    confetti_cooldown = serializers.SerializerMethodField()

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

    def get_confetti_cooldown(self, obj):
        if obj.ad_last_watched:
            unlock_time = (
                (obj.ad_last_watched + timedelta(minutes=CONFETTI_COOLDOWN_MINUTES))
                - timezone.now()
            ).total_seconds()
            if unlock_time > 0:
                hours = int(unlock_time // 3600)
                mins = int((unlock_time % 3600) // 60)
                secs = int((unlock_time % 3600) % 60)
                unlock_countdown = {
                    "hours": hours,
                    "minutes": mins,
                    "seconds": secs,
                }
                return unlock_countdown
        return None

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
            "confetti_cooldown",
            "requested_confetti_alert",
        )


class UserSerializer(serializers.ModelSerializer):
    is_premium = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    confetti = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    approved_holidays = serializers.SerializerMethodField()
    last_online = serializers.SerializerMethodField()
    num_comments = serializers.SerializerMethodField()
    device_active = serializers.SerializerMethodField()

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

    def get_device_active(self, obj):
        return UserProfile.objects.get(user=obj).device_active

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
            "device_active",
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
    avatar = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    time_since_edit = serializers.SerializerMethodField()

    def get_time_since(self, obj):
        time_ago = humanize.naturaltime(timezone.now() - obj.timestamp)
        return normalize_time(time_ago, "precise")

    def get_time_since_edit(self, obj):
        if obj.edited:
            time_ago = humanize.naturaltime(timezone.now() - obj.edited)
            return normalize_time(time_ago, "precise", short=True)

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

    def get_avatar(self, obj):
        profile = UserProfile.objects.get(user=obj.user)
        avatar = (
            f"{CLOUDFRONT_DOMAIN}/{profile.profile_image}"
            if profile and profile.avatar_approved
            else None
        )
        return avatar

    def _get_replies(self, comment):
        """ Recursively get comment reply chain """
        reply_chain = []
        replies = comment.comment_set.all().order_by("-votes", "-id")

        for c in replies:
            reply_chain.append(c)
            if c.comment_set.all().count() > 0:
                child_replies = self._get_replies(c)
                reply_chain.extend(child_replies)

        return reply_chain

    def get_replies(self, obj):
        # TODO limit this / pagination
        replies = self._get_replies(obj)
        return CommentSerializer(replies, many=True).data

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
            "edited",
            "avatar",
            "replies",
            "time_since_edit",
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

    # def get_time_since(self, obj):
    #     if obj.date == timezone.now().date():
    #         return "Today"
    #     return obj.date.strftime("%b %d, %Y")

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
    holiday_id = serializers.SerializerMethodField()

    def get_notification_type(self, obj):
        if obj.notification_type == NEWS_NOTIFICATION:
            return "News"
        elif obj.notification_type == COMMENT_NOTIFICATION:
            return "Comment"
        elif obj.notification_type == POST_NOTIFICATION:
            return "Post"
        elif obj.notification_type == LIKE_NOTIFICATION:
            return "Like"

    def get_holiday_id(self, obj):
        try:
            if obj.notification_type == LIKE_NOTIFICATION:
                liked_post = Post.objects.filter(pk=obj.notification_id).first()
                if liked_post:
                    return liked_post.holiday.id
            else:
                # Directly linked to holiday
                entity = (
                    get_model("api", self.get_notification_type(obj))
                    .objects.filter(pk=obj.notification_id)
                    .first()
                )
                if entity:
                    return entity.holiday.id
        except AttributeError:
            logger.warning(
                f"{obj.notification_type} notification is not linked to holiday."
            )
        return None

    def get_time_since(self, obj):
        time_ago = humanize.naturaltime(timezone.now() - obj.timestamp)
        return normalize_time(time_ago, "precise")

    def get_icon(self, obj):
        profile = None

        if obj.notification_type == COMMENT_NOTIFICATION:
            c = Comment.objects.filter(id=obj.notification_id).first()
            if c:
                profile = UserProfile.objects.filter(user=c.user).first()

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
            "holiday_id",
        )


class PostSerializer(serializers.ModelSerializer):
    time_since = serializers.SerializerMethodField()
    deleted = serializers.BooleanField()
    time_since_edit = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    def get_user(self, obj):
        return obj.user.username

    def get_time_since(self, obj):
        time_ago = humanize.naturaltime(timezone.now() - obj.timestamp)
        return normalize_time(time_ago, "precise", short=True)

    def get_time_since_edit(self, obj):
        if obj.edited:
            time_ago = humanize.naturaltime(timezone.now() - obj.edited)
            return normalize_time(time_ago, "precise", short=True)

    def get_avatar(self, obj):
        profile = UserProfile.objects.get(user=obj.user)
        avatar = (
            f"{CLOUDFRONT_DOMAIN}/{profile.profile_image}"
            if profile and profile.avatar_approved
            else None
        )
        return avatar

    def get_liked(self, obj):
        username = self.context.get("username", None)
        if username:
            liked = obj.user_likes.filter(username=username).exists()
            return liked
        else:
            return False

    def get_replies(self, comment, username):
        """ Recursively get comment reply chain """
        reply_chain = []
        replies = comment.comment_set.all().order_by("-votes", "-id")

        for c in replies:
            reply_chain.append(c)
            if c.comment_set.all().count() > 0:
                child_replies = self.get_replies(c, username)
                reply_chain.extend(child_replies)

        return reply_chain

    def get_comments(self, obj):
        # TODO possibly limit these results for pagination
        comments = Comment.objects.filter(parent_post=obj, deleted=False)
        username = self.context.get("username", None)
        if username:
            profile = UserProfile.objects.get(user__username=username)
            blocked_users = profile.blocked_users.all()
            reported_comments = profile.reported_comments.all().only("id")
            comments = comments.exclude(user__in=blocked_users).exclude(
                id__in=reported_comments
            )
        comments = comments.order_by("-id")
        data = CommentSerializer(comments, many=True).data
        return data

    class Meta:
        model = Post
        fields = "__all__"
