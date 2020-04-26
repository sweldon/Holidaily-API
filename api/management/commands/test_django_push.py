from django.core.management.base import BaseCommand
from push_notifications.models import APNSDevice

from api.models import UserProfile
from django.contrib.auth.models import User


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--username")

    def handle(self, *args, **options):

        username = options["username"]
        device_id = UserProfile.objects.get(user__username=username).device_id
        user = User.objects.get(username=username)
        device, created = APNSDevice.objects.get_or_create(
            registration_id=device_id, user=user
        )
        device.send_message(
            message={
                "title": "Today in History",
                "body": "The Hubble space telescope was placed "
                "into orbit by Discovery, in 1990.",
            },
            extra={"push_type": "news"},
            badge=1,
        )
