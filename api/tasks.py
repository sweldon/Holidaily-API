from logging import getLogger
from typing import Tuple
from celery import shared_task
from django.contrib.auth.models import User

from api.models import UserProfile
from holidaily.helpers.notification_helpers import send_push_to_user, send_email_to_user
from django.core.cache import cache

logger = getLogger("holidaily")


@shared_task
def confetti_notification(user_id: int) -> Tuple[bool, str]:
    cache_key = f"confetti_alert_lock_{user_id}"
    # Protection against accidental spam
    if not cache.add(cache_key, 1, 60 * 10):
        return False, "Cache lock triggered on confetti notification"
    user = User.objects.get(id=user_id)
    profile = UserProfile.objects.get(user=user)
    # Double check they haven't disabled it
    if profile.requested_confetti_alert:
        push_sent = send_push_to_user(
            user,
            f"Confetti is Ready!",
            f"Cooldown has expired and you can now get more confetti!",
            "confetti",
        )
        if push_sent:
            return True, f"{user.username} notified by push"
        else:
            email_sent = send_email_to_user(user, "confetti")
            if email_sent:
                return True, f"{user.username} notified by email"
        return False, f"{user.username} could not be notified by push or email"
    return False, f"{user.username} disabled confetti notification"
