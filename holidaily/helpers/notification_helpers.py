import re
from typing import Union, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from push_notifications.apns import APNSServerError
from push_notifications.models import APNSDevice, GCMDevice

from api.constants import (
    IOS,
    DEFAULT_SLACK_CHANNEL,
    HOLIDAY_SUBMISSION_REWARD,
    COMMENT_NOTIFICATION,
    POST_NOTIFICATION,
    LIKE_NOTIFICATION,
    HOLIDAY_NOTIFICATION,
    LIKE_COMMENT_NOTIFICATION,
)
from api.models import UserProfile, Comment, UserNotifications, Holiday, Post
from holidaily.settings import SLACK_CLIENT
import logging

logger = logging.getLogger("holidaily")


def add_notification(
    n_id: int, n_type: int, user: User, content: str, title: str
) -> Optional[UserNotifications]:
    """
    Add a new notification for users
    :param n_id: notification id, pk
    :param n_type: notification type
    :param user: user to receive notification
    :param content: body of notification
    :param title: title of notification
    :return: the new notification
    """
    if UserNotifications.objects.filter(
        notification_id=n_id, notification_type=n_type, user=user
    ).exists():
        return
    new_notification = UserNotifications.objects.create(
        notification_id=n_id,
        notification_type=n_type,
        user=user,
        content=content,
        title=title,
    )
    return new_notification


def send_email_to_user(
    user: User, notif_obj: Union[UserNotifications, Holiday, str], **kwargs
) -> bool:
    """ Send an email to a user. Returns True if success, False otherwise. """
    email_data = {
        "unsubscribe_link": f"https://holidailyapp.com/portal/unsubscribe/?user={user.username}"
    }
    profile = UserProfile.objects.filter(
        user=user, logged_out=False, emails_enabled=True
    ).first()

    if not profile:
        return False

    if isinstance(notif_obj, UserNotifications):
        if notif_obj.notification_type == COMMENT_NOTIFICATION:
            comment = Comment.objects.filter(id=notif_obj.notification_id).first()
            if not comment:
                return False

            author = comment.user
            author_profile = UserProfile.objects.filter(user=author).first()
            if not author_profile:
                logger.error(f"User for notification has no profile: {author.username}")
                return False

            author_avatar = (
                author_profile.avatar_s3_path
                if author_profile.avatar_s3_path and author_profile.avatar_approved
                else f"https://holidailyapp.com/static/base/img/default_user_128.png"
            )
            subject = f"{author} mentioned you"
            template = "portal/notification_reminder.html"
            email_data["user"] = user
            email_data["author"] = author
            email_data["icon"] = author_avatar
            email_data["comment"] = comment
            email_data["holiday"] = comment.holiday
        else:
            return False

    elif isinstance(notif_obj, Holiday):
        approval = kwargs.get("approval", False)
        if approval:
            subject = "Holiday Approved"
            template = "portal/holiday_approval.html"
            email_data["holiday"] = notif_obj
            email_data["user"] = user
            email_data["award"] = HOLIDAY_SUBMISSION_REWARD
        else:
            return False

    elif isinstance(notif_obj, str):
        if notif_obj == "confetti":
            subject = "Confetti is Ready"
            template = "portal/rewards.html"
            email_data["user"] = user
    # todo add post type
    else:
        return False

    mail_subject = subject
    html_message = render_to_string(template, email_data)
    activation_email = EmailMultiAlternatives(mail_subject, to=[user.email])
    activation_email.attach_alternative(html_message, "text/html")
    activation_email.send(fail_silently=False)
    return True


def send_push_to_user(
    user: User, title: str, body: str, notif_obj: Union[Comment, Holiday, str], **kwargs
) -> bool:
    """ Send push notification to a user. Returns True if success, False otherwise. """
    extra_data = {}
    profile = UserProfile.objects.filter(user=user, logged_out=False).first()
    if not profile:
        return False
    platform = profile.platform
    unread = UserNotifications.objects.filter(user=user, read=False).count()
    extra_data["unread"] = unread
    if isinstance(notif_obj, (Comment, Post)):
        # This is type "comment" but can technically also be a post.
        # It's handled as a "comment" in app to redirect.
        if isinstance(notif_obj, Comment):
            extra_data["push_type"] = "comment"
            extra_data["comment_id"] = notif_obj.id
        else:
            extra_data["push_type"] = "post"
            extra_data["post_id"] = notif_obj.id
        extra_data["holiday_id"] = notif_obj.holiday.id
        extra_data["content"] = notif_obj.content
        extra_data["comment_user"] = notif_obj.user.username
        extra_data["holiday_name"] = notif_obj.holiday.name
    elif isinstance(notif_obj, Holiday):
        extra_data["push_type"] = "holiday"
        extra_data["holiday_id"] = notif_obj.id
        extra_data["holiday_name"] = notif_obj.name
    elif isinstance(notif_obj, str):
        if notif_obj == "confetti":
            extra_data["push_type"] = "rewards"
        elif notif_obj == "like":
            extra_data["push_type"] = "like"
            holiday_id = kwargs.get("holiday_id")
            holiday_name = kwargs.get("holiday_name")
            extra_data["holiday_id"] = holiday_id
            extra_data["holiday_name"] = holiday_name

            entity_id = kwargs.get("entity_id")
            entity_type = kwargs.get("entity_type")
            extra_data["entity_type"] = entity_type

            if entity_type == "comment":
                extra_data["comment_id"] = entity_id
            else:
                # todo legacy Currently only likes for post <=2.0.1
                # todo this will be none if it's a comment like
                extra_data["post_id"] = entity_id
        else:
            return False
    else:
        return False

    device_class = APNSDevice if platform == IOS else GCMDevice
    device = device_class.objects.filter(user=user).last()
    if not device:
        profile.device_active = False
        profile.save()
        return False

    unread = UserNotifications.objects.filter(user=user, read=False).count()

    if platform == IOS:
        try:
            device.send_message(
                message={"title": title, "body": body}, extra=extra_data, badge=unread,
            )
        except APNSServerError as e:
            logger.error(msg=f"Could not send push to iOS user {user.username}: {e}")
            device.delete()
            profile.device_active = False
            profile.save()
            return False
    else:
        push_sent = device.send_message(
            body, title=title, badge=unread, extra=extra_data
        )
        if not push_sent.get("success"):
            logger.error(
                msg=f"Could not send push to Android user {user.username}: {push_sent.get('results')}"
            )
            device.delete()
            profile.device_active = False
            profile.save()
            return False
    return True


def send_slack(message: str, channel: str = DEFAULT_SLACK_CHANNEL):
    SLACK_CLIENT.chat_postMessage(channel=f"#{channel}", text=message)


def award_and_notify_user_for_holiday(holiday: Holiday) -> bool:
    creator = holiday.creator
    user_profile = UserProfile.objects.filter(user=creator).first()
    if not user_profile:
        return False
    user_profile.confetti += HOLIDAY_SUBMISSION_REWARD
    user_profile.save()

    push_title = "Holiday Approved"
    push_body = f"{holiday.name} was approved and you have been awarded {HOLIDAY_SUBMISSION_REWARD} confetti!"

    add_notification(
        holiday.pk,
        HOLIDAY_NOTIFICATION,
        creator,
        f"{holiday.name} has been approved! You have been awarded {HOLIDAY_SUBMISSION_REWARD} confetti.",
        "Holiday Approved",
    )

    push_sent = send_push_to_user(creator, push_title, push_body, holiday)
    if push_sent:
        holiday.creator_awarded = True
        holiday.save()
        return True
    else:
        email_sent = send_email_to_user(creator, holiday, approval=True)
        if email_sent:
            holiday.creator_awarded = True
            holiday.save()
            return True
    return False


def notify_mentioned_users(notification: Union[Comment, Post]) -> None:

    content = notification.content
    username = notification.user.username
    holiday = notification.holiday
    notification_type = None
    if isinstance(notification, Comment):
        notification_type = COMMENT_NOTIFICATION
    elif isinstance(notification, Post):
        notification_type = POST_NOTIFICATION
    else:
        raise (f"Not a valid notification type: {type(notification_type)}")

    mentions = list(set(re.findall(r"@([^\s.,\?\"\'\;]+)", content)))
    for user_mention in mentions:
        if user_mention == username:
            continue
        # Get user profiles, exclude self if user mentions themself for some reason
        user_to_notify = User.objects.filter(username=user_mention).first()
        if user_to_notify:
            n = add_notification(
                notification.pk,
                notification_type,
                user_to_notify,
                content,
                f"{username} on {holiday.name}",
            )
            push_sent = send_push_to_user(
                user_to_notify,
                f"{username} mentioned you on {holiday.name}",
                f"{content[:100]}{'...' if len(content) > 100 else ''}",
                notification,
            )
            if not push_sent and settings.EMAIL_NOTIFICATIONS_ENABLED:
                send_email_to_user(user_to_notify, n)


def notify_liked_user(obj: Union[Post, Comment], user: User) -> bool:
    """
    This should accept any entity that can be liked
    :param obj: The entity being liked
    :param user: The user that liked the entity
    :return: True/False depending on success
    """
    entity = obj.__class__.__name__.lower()
    notif_type = LIKE_NOTIFICATION if entity == "post" else LIKE_COMMENT_NOTIFICATION
    add_notification(
        obj.pk,
        notif_type,
        obj.user,
        f"{user.username} liked your {entity} on {obj.holiday.name}",
        f"{user.username}",
    )
    push_sent = send_push_to_user(
        obj.user,
        f"{user.username}",
        f"{user.username} liked your {entity} on {obj.holiday.name}",
        "like",
        holiday_id=obj.holiday.id,
        holiday_name=obj.holiday.name,
        entity_id=obj.id,
        entity_type=entity,
    )
    return push_sent
