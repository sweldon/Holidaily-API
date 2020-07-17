from push_notifications.models import APNSDevice, GCMDevice

from api.constants import (
    DEFAULT_SLACK_CHANNEL,
    IOS,
    ANDROID,
)
from holidaily.settings import SLACK_CLIENT


def normalize_time(time_ago: str, time_type: str) -> str:
    """
    Create a human readable since since string, i.e. 2 minutes ago
    """
    if time_type == "precise":
        return time_ago
    elif time_type == "relative":
        if (
            "hours" in time_ago
            or "minutes" in time_ago
            or time_ago == "now"
            or time_ago == "just now"
        ):
            return "Today"
        elif time_ago == "1 day ago" or time_ago == "a day ago":
            return "Yesterday"
        else:
            return time_ago


def send_slack(message, channel=DEFAULT_SLACK_CHANNEL):
    SLACK_CLIENT.chat_postMessage(channel=f"#{channel}", text=message)


# TODO implement send_push_to_all_users(platform=android,ios,none/both)


def send_push_to_user(user, title, body, notif_obj=None):
    from api.models import UserProfile, Comment, UserNotifications

    # TODO determine badge count on IOS by UserNotifications where read=False
    extra_data = {}
    profile = UserProfile.objects.filter(user=user, logged_out=False).first()
    if not profile:
        return
    platform = profile.platform
    if isinstance(notif_obj, Comment):
        # notif_obj is a Comment
        extra_data["push_type"] = "comment"
        extra_data["holiday_id"] = notif_obj.holiday.id
        extra_data["comment_id"] = notif_obj.id
        extra_data["content"] = notif_obj.content
        extra_data["comment_user"] = notif_obj.user.username
        extra_data["holiday_name"] = notif_obj.holiday.name
    else:
        # TODO implement other notification types when they exist
        return
    device_class = APNSDevice if platform == IOS else GCMDevice
    device = device_class.objects.filter(user=user).last()

    if device:
        unread = UserNotifications.objects.filter(user=user, read=False).count()
        if platform == IOS:
            device.send_message(
                message={"title": title, "body": body}, extra=extra_data, badge=unread,
            )
        else:
            device.send_message(body, title=title, badge=unread, extra=extra_data)


def sync_devices(registration_id, platform, user=None):
    device_class = APNSDevice if platform == IOS else GCMDevice
    # If no user, log device of anonymous user to be assigned later
    if user is None:
        if not device_class.objects.filter(registration_id=registration_id):
            if platform == ANDROID:
                device_class.objects.create(
                    registration_id=registration_id, cloud_message_type="FCM"
                )
            else:
                device_class.objects.create(registration_id=registration_id)
    else:
        existing_device = device_class.objects.filter(user=user).last()
        if existing_device:
            if existing_device.registration_id != registration_id:
                print(
                    f"Updating {platform} device id for user {user.username} from "
                    f"{existing_device.registration_id } to {registration_id}"
                )
                existing_device.registration_id = registration_id
                existing_device.active = True
                existing_device.save()
                # Existing user got a new phone, or reinstalled and logged back in
                existing_unassigned = device_class.objects.filter(
                    registration_id=registration_id, user__isnull=True
                ).last()
                if existing_unassigned:
                    existing_unassigned.delete()
        else:
            unassigned_device = device_class.objects.filter(
                registration_id=registration_id, user__isnull=True
            ).last()
            if unassigned_device:
                print("assigning unassigned device")
                # Replace unassigned device with logged in user
                unassigned_device.user = user
                unassigned_device.active = True
                unassigned_device.save()
            else:
                print("creating new device")
                if platform == ANDROID:
                    device_class.objects.create(
                        registration_id=registration_id,
                        cloud_message_type="FCM",
                        user=user,
                    )
                else:
                    device_class.objects.create(
                        registration_id=registration_id, user=user
                    )
