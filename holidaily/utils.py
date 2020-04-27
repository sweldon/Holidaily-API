from push_notifications.models import APNSDevice, GCMDevice

from api.constants import (
    DEFAULT_SLACK_CHANNEL,
    IOS,
    ANDROID,
    NEWS_NOTIFICATION,
    HOLIDAY_NOTIFICATION,
)
from holidaily.settings import (
    SLACK_CLIENT,
    PUSH_ENDPOINT_IOS,
    PUSH_ENDPOINT_ANDROID,
    APPCENTER_API_KEY,
)
import requests


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


def send_push(title, body, notif_type=None, notif_id=None, users=None):
    from api.models import UserProfile

    custom_data = {}
    target_data = None
    profiles = UserProfile.objects.filter(user__in=users) if users else None
    targets = [u.device_id for u in profiles] if users else None
    if targets:
        target_data = {
            "type": "devices_target",
            "devices": targets,
        }
    if notif_type == NEWS_NOTIFICATION:
        custom_data["news"] = "true"
    elif notif_type == HOLIDAY_NOTIFICATION:
        custom_data["holiday_id"] = notif_id
    data = {
        "notification_content": {
            "name": "Holidaily Notification",
            "title": title,
            "body": body,
            "custom_data": custom_data,
        },
        "notification_target": target_data,
    }
    headers = {"X-API-Token": APPCENTER_API_KEY}

    if profiles and profiles.count() == 1:
        profile = profiles.first()
        user_platform = profile.platform
        if user_platform == IOS:
            requests.post(PUSH_ENDPOINT_IOS, headers=headers, json=data)
        elif user_platform == ANDROID:
            requests.post(PUSH_ENDPOINT_ANDROID, headers=headers, json=data)
    else:
        requests.post(PUSH_ENDPOINT_ANDROID, headers=headers, json=data)
        requests.post(PUSH_ENDPOINT_IOS, headers=headers, json=data)


def sync_devices(registration_id, platform, user=None):
    if registration_id == "none":  # Firebase default sometimes on first launch
        return
    device_class = APNSDevice if platform == IOS else GCMDevice
    # If no user, log device of anonymous user to be assigned later
    if user is None:
        device, created = device_class.objects.get_or_create(
            registration_id=registration_id
        )
        if created:
            print(f"Created new {platform} device for anonymous user {registration_id}")
            if platform == ANDROID:
                device.cloud_message_type = "FCM"
                device.save()
    else:
        existing_device = device_class.objects.filter(user=user).first()
        if existing_device:
            if existing_device.registration_id != registration_id:
                print(
                    f"Updating {platform} device id for user {user.username} from "
                    f"{existing_device.registration_id } to {registration_id}"
                )
                existing_device.registration_id = registration_id
                existing_device.save()
        else:
            print(
                f"Adding new {platform} device for user {user.username} {registration_id}"
            )
            new_device, _ = device_class.objects.get_or_create(
                registration_id=registration_id
            )
            new_device.user = user
            if platform == ANDROID:
                new_device.cloud_message_type = "FCM"
            new_device.save()
