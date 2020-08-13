from django.core.management.base import BaseCommand
from push_notifications.models import GCMDevice, APNSDevice

from api.models import Holiday
from django.utils import timezone
import random


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

        # FCM/APNs logic
        androids = GCMDevice.objects.all()
        iphones = APNSDevice.objects.all()

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
