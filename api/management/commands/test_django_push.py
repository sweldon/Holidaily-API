from django.core.management.base import BaseCommand
from push_notifications.models import APNSDevice, GCMDevice
from api.models import UserProfile
from api.models import Holiday
from django.utils import timezone
import random


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--username")
        parser.add_argument("--platform")
        parser.add_argument("--type")

    def handle(self, *args, **options):
        username = options["username"]
        platform = options["platform"]
        push_type = options["type"]
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
        device_class = APNSDevice if platform == "ios" else GCMDevice
        device_id = UserProfile.objects.get(user__username=username).device_id
        device = device_class.objects.filter(registration_id=device_id).first()

        extra_data = {}
        if push_type == "holiday":
            title = day_name
            body = push
            extra_data = {
                "holiday_id": id,
                "holiday_name": day_name,
                "push_type": "holiday",
            }
        elif push_type == "comment":
            title = "steve mentioned you in a comment!"
            body = "Some test comment data"
            extra_data = {
                "holiday_id": 234,
                "push_type": "comment",
                "comment_id": 275,
                "comment_user": "steve",
            }
        elif push_type == "news":
            title = "Holidaily Update"
            body = "Some news from Holidaily"
            extra_data = {"news": "true", "push_type": "news"}

        if platform == "ios":
            device.send_message(
                message={"title": title, "body": body}, extra=extra_data, badge=1,
            )
        else:
            device.send_message(body, title=title, badge=1, extra=extra_data)
