from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles
from rest_framework.authtoken.models import Token
import timeago
from django.utils import timezone
from holidaily.utils import normalize_time

LEXERS = [item for item in get_all_lexers() if item[1]]
LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
STYLE_CHOICES = sorted([(item, item) for item in get_all_styles()])


class UserProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,)
    active = models.BooleanField(default=True)
    device_id = models.CharField(max_length=100)
    rewards = models.IntegerField(default=0)
    profile_image = models.TextField(blank=True, null=True)
    premium = models.BooleanField(default=False)
    premium_id = models.TextField(blank=True, null=True)
    premium_token = models.TextField(blank=True, null=True)
    premium_state = models.TextField(blank=True, null=True)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Create API token for new users
    """
    if created:
        Token.objects.create(user=instance)


class Holiday(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    votes = models.IntegerField(default=0)
    blurb = models.TextField(null=True)
    image = models.TextField(null=True)
    date = models.DateField(null=False)

    @property
    def comments(self):
        return self.comment_set.all()

    @property
    def num_comments(self):
        return self.comment_set.all().count()

    @property
    def time_since(self):
        time_ago = timeago.format(self.date, timezone.now().today())
        return normalize_time(time_ago, "holiday")


class Comment(models.Model):
    content = models.TextField()
    holiday = models.ForeignKey(Holiday, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name="user_comments", on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField()
    votes = models.IntegerField(default=0)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)

    @property
    def time_since(self):
        time_ago = timeago.format(self.timestamp, timezone.now())
        return normalize_time(time_ago, "comment")
