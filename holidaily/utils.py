from push_notifications.models import APNSDevice, GCMDevice

from api.constants import (
    IOS,
    ANDROID,
)


def normalize_time(time_ago: str, time_type: str, short=False) -> str:
    """
    Create a human readable since since string, i.e. 2 minutes ago
    """
    if time_type == "precise":
        if short:
            time_ago = (
                time_ago.replace("hours ago", "h")
                .replace("an hour ago", "1h")
                .replace("minutes ago", "m")
                .replace("a minute ago", "1m")
                .replace("seconds ago", "s")
                .replace("a second ago", "1s")
                .replace("days ago", "d")
                .replace("a day ago", "1d")
                .replace("year ago", "y")
                .replace("years ago", "y")
                .replace(" ", "")
            )
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
