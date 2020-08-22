from logging import getLogger
from typing import Tuple
from celery.decorators import task
from django.contrib.auth.models import User

from api.models import UserProfile
from holidaily.helpers.notification_helpers import send_push_to_user

logger = getLogger("holidaily")


@task()
def confetti_notification(user_id: int) -> Tuple[bool, str]:
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
            return False, f"{user.username} push failed"
        # if not push_sent and settings.EMAIL_NOTIFICATIONS_ENABLED:
        #     email_sent = send_email_to_user(user, n)
        #     if email_sent:
        #         return True, f"{user.username} notified by email"
        # return False, f"{user.username} could not be notified by push or email"
    return False, f"{user.username} disabled confetti notification"
