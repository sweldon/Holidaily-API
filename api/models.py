from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles
from rest_framework.authtoken.models import Token


LEXERS = [item for item in get_all_lexers() if item[1]]
LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
STYLE_CHOICES = sorted([(item, item) for item in get_all_styles()])


class Month(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.ForeignKey(
        User,
        related_name="user_profiles",
        related_query_name="user_profile",
        on_delete=models.CASCADE,
    )
    active = models.BooleanField(default=True)
    device_id = models.CharField(max_length=50)
    rewards = models.IntegerField(default=0)
    profile_image = models.TextField()
    premium = models.BooleanField(default=False)
    premium_id = models.CharField(max_length=50)
    premium_token = models.TextField()
    premium_state = models.CharField(max_length=50)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Create API token for new users
    """
    if created:
        Token.objects.create(user=instance)
