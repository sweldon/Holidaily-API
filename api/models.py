from builtins import Exception

import boto3
from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles

from api.constants import NEWS_NOTIFICATION, S3_BUCKET_IMAGES
from holidaily.settings import (
    HOLIDAY_IMAGE_WIDTH,
    HOLIDAY_IMAGE_HEIGHT,
    APPCENTER_API_KEY,
    PUSH_ENDPOINT_ANDROID,
    PUSH_ENDPOINT_IOS,
)
from holidaily.utils import normalize_time
import humanize
from django.utils import timezone
from django.db.models import Sum
import requests
from PIL import Image
from io import BytesIO

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
NOTIFICATION_TYPES = (
    (0, "comment"),
    (1, "news"),
)


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

    @property
    def num_comments(self):
        return Comment.objects.filter(user=self.user).count()

    @property
    def holiday_submissions(self):
        return Holiday.objects.filter(creator=self.user).count()

    @property
    def approved_holidays(self):
        return Holiday.objects.filter(creator=self.user, active=True).count()

    @property
    def confetti(self):
        user_profile = UserProfile.objects.get(user=self.user)
        points = user_profile.rewards
        comment_votes = Comment.objects.filter(user=self.user).aggregate(Sum("votes"))
        if comment_votes["votes__sum"]:
            comment_points = (
                comment_votes["votes__sum"] if comment_votes["votes__sum"] > 0 else 0
            )
        else:
            comment_points = 0
        points += comment_points
        return points


# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_auth_token(sender, instance=None, created=False, **kwargs):
#     """
#     Create API token for new users
#     """
#     if created:
#         Token.objects.create(user=instance)


class Holiday(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    votes = models.IntegerField(default=0)
    push = models.TextField(null=True, blank=True)
    image = models.TextField(null=True)
    image_name = models.CharField(max_length=100, default=None, null=True, blank=True)
    date = models.DateField(null=False)
    # Creator is null for regular holidays, set for user submitted
    creator = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    active = models.BooleanField(default=True)
    blurb = models.TextField(null=True)
    IMAGE_FORMATS = (("jpeg", "jpeg"), ("png", "png"))
    image_format = models.CharField(
        max_length=10, choices=IMAGE_FORMATS, default="jpeg"
    )

    @property
    def num_comments(self):
        return self.comment_set.all().count()

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

    def save(self, *args, **kwargs):

        if self.image:
            try:
                file_name = f"{self.name.strip().replace(' ', '-')}.{self.image_format}"
                image_size = (HOLIDAY_IMAGE_WIDTH, HOLIDAY_IMAGE_HEIGHT)
                image_data = requests.get(self.image).content
                image_object = Image.open(BytesIO(image_data))
                image_object.thumbnail(image_size)

                byte_arr = BytesIO()
                image_object.save(byte_arr, format=self.image_format)
                s3_client = boto3.resource("s3")
                s3_client.Bucket("holiday-images").put_object(
                    Key=file_name, Body=byte_arr.getvalue()
                )
                self.image_name = file_name
            except Exception as e:  # noqa
                print(f"Could not save image: {e}")
        super(Holiday, self).save(*args, **kwargs)


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

    @property
    def replies(self):
        replies = Comment.objects.get(parent=self)
        return replies

    @property
    def time_since(self):
        time_ago = humanize.naturaltime(timezone.now() - self.timestamp)
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
    title = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        super(UserNotifications, self).save(*args, **kwargs)
        if self.notification_type == NEWS_NOTIFICATION:
            data = {
                "notification_content": {
                    "name": "Announcement",
                    "title": self.title,
                    "body": self.content,
                    "custom_data": {"news": "true"},
                },
                "notification_target": None,
            }
            headers = {"X-API-Token": APPCENTER_API_KEY}
            requests.post(PUSH_ENDPOINT_ANDROID, headers=headers, json=data)
            requests.post(PUSH_ENDPOINT_IOS, headers=headers, json=data)
