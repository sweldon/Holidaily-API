from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles

from api.constants import S3_BUCKET_IMAGES
from holidaily.settings import (
    HOLIDAY_IMAGE_WIDTH,
    HOLIDAY_IMAGE_HEIGHT,
)
from holidaily.utils import normalize_time
import humanize
from django.utils import timezone


LEXERS = [item for item in get_all_lexers() if item[1]]
LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
STYLE_CHOICES = sorted([(item, item) for item in get_all_styles()])
VOTE_CHOICES = (
    (0, "down"),
    (1, "up"),
    (2, "neutral_from_down"),
    (3, "neutral_from_up"),
    (4, "up_from_down"),
    (5, "down_from_up"),
)
NOTIFICATION_TYPES = ((0, "comment"), (1, "news"), (2, "holiday"))


class UserProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,)
    active = models.BooleanField(default=True)
    device_id = models.TextField(blank=True, null=True)
    rewards = models.IntegerField(default=0)
    profile_image = models.TextField(blank=True, null=True)
    premium = models.BooleanField(default=False)
    premium_id = models.TextField(blank=True, null=True)
    premium_token = models.TextField(blank=True, null=True)
    premium_state = models.TextField(blank=True, null=True)
    logged_out = models.BooleanField(default=False)
    blocked_users = models.ManyToManyField(
        User, related_name="blocked_users", blank=True
    )
    reported_comments = models.ManyToManyField(
        "Comment", related_name="reported_comments", blank=True
    )
    confetti = models.IntegerField(default=0)
    platform = models.CharField(max_length=50, default=None, blank=True, null=True)
    version = models.CharField(max_length=50, default=None, blank=True, null=True)
    last_launched = models.DateTimeField(blank=True, null=True)
    avatar_approved = models.BooleanField(default=False)
    referrer = models.CharField(max_length=50, blank=True, null=True)
    emails_enabled = models.BooleanField(default=True)
    device_active = models.BooleanField(default=True)
    ad_last_watched = models.DateTimeField(
        blank=True, null=True, help_text="Last time the user watched a reward ad"
    )
    requested_confetti_alert = models.BooleanField(default=False)

    def avatar_s3_path(self):
        if not self.profile_image:
            return None
        return f"{S3_BUCKET_IMAGES}/{self.profile_image}"

    def avatar_preview(self):
        return (
            mark_safe(
                '<img src="%s" width="%s" height="%s" />'
                % (
                    f"{S3_BUCKET_IMAGES}/{self.profile_image}",
                    HOLIDAY_IMAGE_WIDTH / 4,
                    HOLIDAY_IMAGE_HEIGHT / 4,
                )
            )
            if self.profile_image
            else None
        )

    def avatar_full(self):
        return (
            mark_safe(
                '<img src="%s" width="%s" height="%s" />'
                % (
                    f"{S3_BUCKET_IMAGES}/{self.profile_image}",
                    HOLIDAY_IMAGE_WIDTH,
                    HOLIDAY_IMAGE_HEIGHT,
                )
            )
            if self.profile_image
            else None
        )

    avatar_preview.short_description = "Avatar"
    avatar_full.short_description = "Avatar"

    @property
    def num_comments(self):
        return Comment.objects.filter(user=self.user).count()

    @property
    def holiday_submissions(self):
        return Holiday.objects.filter(creator=self.user).count()

    @property
    def approved_holidays(self):
        return Holiday.objects.filter(creator=self.user, active=True).count()


class Holiday(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    votes = models.IntegerField(default=0)
    push = models.TextField(
        null=True, blank=True, help_text="Push notification message sent out to users"
    )
    image = models.TextField(
        null=True, blank=True, help_text="Paste in URL to image for upload"
    )
    uploaded_image = models.ImageField(
        blank=True, null=True, help_text="Upload image from your device"
    )
    image_name = models.CharField(max_length=100, default=None, null=True, blank=True)
    date = models.DateField(null=False)
    # Creator is null for regular holidays, set for user submitted
    creator = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    active = models.BooleanField(
        default=True,
        help_text="Will holiday appear in the app. If false, will still appear if no creator",
    )
    blurb = models.TextField(
        null=True, help_text="Short description appearing in Holiday list"
    )
    IMAGE_FORMATS = (("jpeg", "jpeg"), ("png", "png"))
    image_format = models.CharField(
        max_length=10, choices=IMAGE_FORMATS, default="jpeg"
    )
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    creator_awarded = models.BooleanField(
        default=False,
        help_text="Has user already been sent a push notification and awarded confetti",
    )

    @property
    def num_comments(self):
        # Note, this doesn't currently include replies
        return self.comment_set.filter(deleted=False).count()

    def get_image(self):
        return mark_safe(
            '<img src="%s" width="%s" height="%s" />'
            % (
                f"{S3_BUCKET_IMAGES}/{self.image_name}",
                HOLIDAY_IMAGE_WIDTH,
                HOLIDAY_IMAGE_HEIGHT,
            )
        )

    def get_image_small(self):
        return mark_safe(
            '<img src="%s" width="%s" height="%s" />'
            % (
                f"{S3_BUCKET_IMAGES}/{self.image_name}",
                HOLIDAY_IMAGE_WIDTH / 2,
                HOLIDAY_IMAGE_HEIGHT / 2,
            )
        )

    get_image.short_description = "Image Preview"
    get_image_small.short_description = "Image Preview"

    def __str__(self):
        return self.name


class Comment(models.Model):
    content = models.TextField()
    holiday = models.ForeignKey(Holiday, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name="user_comments", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField()
    votes = models.IntegerField(default=0)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)
    reports = models.IntegerField(default=0)
    edited = models.DateTimeField(blank=True, null=True)

    @property
    def replies(self):
        replies = Comment.objects.get(parent=self)
        return replies

    @property
    def time_since(self):
        time_ago = humanize.naturaltime(timezone.now() - self.timestamp)
        return normalize_time(time_ago, "precise")

    @property
    def time_since_edit(self):
        if self.edited:
            time_ago = humanize.naturaltime(timezone.now() - self.edited)
            return normalize_time(time_ago, "precise")

    def __str__(self):
        return f"{self.content[:100]}..."


class UserHolidayVotes(models.Model):
    user = models.ForeignKey(User, models.CASCADE)
    holiday = models.ForeignKey(Holiday, on_delete=models.CASCADE)
    choice = models.IntegerField(choices=VOTE_CHOICES)


class UserCommentVotes(models.Model):
    user = models.ForeignKey(User, models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    choice = models.IntegerField(choices=VOTE_CHOICES)


class UserNotifications(models.Model):
    # Dont need a user if you want to post news to everyone
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    notification_id = models.IntegerField(
        blank=True, null=True
    )  # FK to associated notification_type
    notification_type = models.IntegerField(choices=NOTIFICATION_TYPES)
    read = models.BooleanField(default=False)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=150)

    def save(self, *args, **kwargs):
        super(UserNotifications, self).save(*args, **kwargs)
        # TODO update this to new FCM/APNs format
        # send_push_to_all_users or send_push_to_user(self.user)
        # if self.notification_type in [NEWS_NOTIFICATION, HOLIDAY_NOTIFICATION]:
        #     target = [self.user] if self.user else None
        #     send_push(
        #         title=self.title,
        #         body=self.content,
        #         notif_type=self.notification_type,
        #         users=target,
        #         notif_id=self.notification_id,
        #     )


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)
    holiday = models.ForeignKey(Holiday, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    likes = models.IntegerField(default=0)
    deleted = models.BooleanField(default=False)
    reports = models.IntegerField(default=0)
    edited = models.DateTimeField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
