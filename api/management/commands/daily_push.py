from django.core.management.base import BaseCommand
from push_notifications.models import GCMDevice, APNSDevice

from api.models import Holiday, UserProfile
from django.utils import timezone
import requests
import random
from holidaily.settings import APPCENTER_API_KEY
from django.db.models.functions import Length


class Command(BaseCommand):
    def handle(self, *args, **options):
        today = timezone.now().date()
        todays_holidays = (
            Holiday.objects.filter(date=today, active=True)
            .exclude(push__isnull=True)
            .exclude(push__exact="")
        )
        if todays_holidays.count() == 0:
            return "No holidays available"
        random_day = random.choice(todays_holidays)
        push = random_day.push if random_day.push else "Check out today's holidays!"
        day_name = random_day.name
        id = random_day.id

        # Old AppCenter Logic
        old_devices = list(
            UserProfile.objects.annotate(text_len=Length("device_id"))
            .filter(text_len=36)
            .values_list("device_id", flat=True)
        )
        android_url = (
            "https://api.appcenter.ms/v0.1/apps/steven.d.weldon-gmail.com/Holidaily-Android-Dev/push/"
            "notifications"
        )
        ios_url = "https://api.appcenter.ms/v0.1/apps/steven.d.weldon-gmail.com/Holidaily-IOS/push/notifications"
        data = {
            "notification_content": {
                "name": "Daily Holiday Update",
                "title": day_name,
                "body": push,
                "custom_data": {"holiday_id": id, "holiday_name": day_name},
            },
            "notification_target": {"type": "devices_target", "devices": old_devices},
        }
        headers = {"X-API-Token": APPCENTER_API_KEY}
        requests.post(android_url, headers=headers, json=data)
        requests.post(ios_url, headers=headers, json=data)

        # New FCM/APNs logic
        # Now send to new devices, only if the user has gotten a new token
        androids = GCMDevice.objects.all().exclude(registration_id__in=old_devices)
        iphones = APNSDevice.objects.all().exclude(registration_id__in=old_devices)

        iphones.send_message(
            message={"title": day_name, "body": push},
            extra={"holiday_id": id, "holiday_name": day_name, "push_type": "holiday"},
            badge=1,
        )
        androids.send_message(
            push,
            title=day_name,
            badge=1,
            extra={"holiday_id": id, "holiday_name": day_name, "push_type": "holiday"},
        )

        # Delete invalid devices
        GCMDevice.objects.filter(active=False).delete()
        APNSDevice.objects.filter(active=False).delete()
