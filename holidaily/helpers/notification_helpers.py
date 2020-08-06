from typing import Union

from django.contrib.auth.models import User
from push_notifications.apns import APNSServerError
from push_notifications.models import APNSDevice, GCMDevice

from api.constants import IOS, DEFAULT_SLACK_CHANNEL, HOLIDAY_SUBMISSION_REWARD
from api.models import (
    UserProfile,
    Comment,
    UserNotifications,
    Holiday,
)
from holidaily.settings import SLACK_CLIENT


def add_notification(
    n_id: int, n_type: int, user: User, content: str, title: str
) -> UserNotifications:
    """
    Add a new notification for users
    :param n_id: notification id, pk
    :param n_type: notification type
    :param user: user to receive notification
    :param content: body of notification
    :param title: title of notification
    :return: the new notification
    """
    new_notification = UserNotifications.objects.create(
        notification_id=n_id,
        notification_type=n_type,
        user=user,
        content=content,
        title=title,
    )
    return new_notification


def send_push_to_user(
    user: User, title: str, body: str, notif_obj: Union[Comment, Holiday]
) -> bool:
    extra_data = {}
    profile = UserProfile.objects.filter(user=user, logged_out=False).first()
    if not profile:
        return False
    platform = profile.platform
    unread = UserNotifications.objects.filter(user=user, read=False).count()
    extra_data["unread"] = unread
    if isinstance(notif_obj, Comment):
        extra_data["push_type"] = "comment"
        extra_data["holiday_id"] = notif_obj.holiday.id
        extra_data["comment_id"] = notif_obj.id
        extra_data["content"] = notif_obj.content
        extra_data["comment_user"] = notif_obj.user.username
        extra_data["holiday_name"] = notif_obj.holiday.name
    elif isinstance(notif_obj, Holiday):
        extra_data["push_type"] = "holiday"
        extra_data["holiday_id"] = notif_obj.id
        extra_data["holiday_name"] = notif_obj.name
    else:
        return False

    device_class = APNSDevice if platform == IOS else GCMDevice
    device = device_class.objects.filter(user=user).last()
    if not device:
        return False

    unread = UserNotifications.objects.filter(user=user, read=False).count()

    if platform == IOS:
        try:
            device.send_message(
                message={"title": title, "body": body}, extra=extra_data, badge=unread,
            )
        except APNSServerError as e:
            print(f"[ERROR] Could not send push to iOS user {user.username}: {e}")
            return False
    else:
        push_sent = device.send_message(
            body, title=title, badge=unread, extra=extra_data
        )
        if not push_sent.get("success"):
            print(
                f"[ERROR] Could not send push to Android user {user.username}: {push_sent.get('results')}"
            )
            return False
    return True


def send_slack(message: str, channel: str = DEFAULT_SLACK_CHANNEL):
    SLACK_CLIENT.chat_postMessage(channel=f"#{channel}", text=message)


def award_and_notify_user_for_holiday(holiday: Holiday):
    creator = holiday.creator
    user_profile = UserProfile.objects.filter(user=creator).first()
    if not user_profile:
        return
    user_profile.confetti += HOLIDAY_SUBMISSION_REWARD
    user_profile.save()

    push_title = "Holiday Approved"
    push_body = f"{holiday.name} was approved and you have been awarded {HOLIDAY_SUBMISSION_REWARD} confetti!"

    push_sent = send_push_to_user(creator, push_title, push_body, holiday)
    if push_sent:
        holiday.creator_awarded = True
        holiday.save()
