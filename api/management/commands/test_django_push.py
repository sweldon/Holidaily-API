from django.core.management.base import BaseCommand
from push_notifications.models import APNSDevice, GCMDevice
from api.models import UserProfile
from api.models import Holiday
from django.utils import timezone
import random
from django.contrib.auth.models import User

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--username")
        parser.add_argument("--platform")
        parser.add_argument("--type")
        parser.add_argument("--holiday_name")
        parser.add_argument("--holiday_id")

    def handle(self, *args, **options):
        username = options["username"]
        platform = options["platform"]
        push_type = options["type"]
        holiday_name = options["holiday_name"]
        holiday_id = options["holiday_id"]

        if push_type == "holiday" and not holiday_name and not holiday_id:
            print("Need an id or name for a holiday push")
            return

        if not holiday_name:
            h = Holiday.objects.filter(id=holiday_id).first()
        else:
            h = Holiday.objects.filter(name=holiday_name).first()

        if not h:
            return

        title = f"Holiday Approved"
        body = "Your holiday was approved, and you were awarded 15 confetti! Thanks so much for your contribution to Holidaily!"
        
        if username != "all":
            user = User.objects.get(username=username)
            device_class = APNSDevice if platform == "ios" else GCMDevice
            device = device_class.objects.filter(user=user).first()

        extra_data = {}
        if push_type == "holiday":
            title = title
            body = body
            extra_data = {
                "holiday_id": h.id,
                "holiday_name": h.name,
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

        if username == "all":
            androids = GCMDevice.objects.all()
            iphones = APNSDevice.objects.all()
            iphones.send_message(
                    message={"title": title, "body": body}, extra=extra_data, badge=1,
                )
            androids.send_message(body, title=title, badge=1, extra=extra_data)
        else:
            if platform == "ios":
                device.send_message(
                    message={"title": title, "body": body}, extra=extra_data, badge=1,
                )
            else:
                device.send_message(body, title=title, badge=1, extra=extra_data)

