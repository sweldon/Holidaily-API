from django.core.management.base import BaseCommand
from api.models import Holiday
from django.utils import timezone
import requests
import random
from holidaily.settings import APPCENTER_API_KEY


class Command(BaseCommand):
    def handle(self, *args, **options):
        today = timezone.now().date()
        todays_holidays = Holiday.objects.filter(date=today)
        random_day = random.choice(todays_holidays)
        push = random_day.push
        day_name = random_day.name
        id = random_day.id
        android_url = 'https://api.appcenter.ms/v0.1/apps/steven.d.weldon-gmail.com/Holidaily-Android-Dev/push/notifications'
        ios_url = 'https://api.appcenter.ms/v0.1/apps/steven.d.weldon-gmail.com/Holidaily-IOS/push/notifications'
        data = {"notification_content": {"name": "Daily Holiday Update", "title": day_name, "body": push,
                                         "custom_data": {"holiday_id": id, "holiday_name": day_name}},
                "notification_target": None}
        headers = {"X-API-Token": APPCENTER_API_KEY}
        r_android = requests.post(android_url, headers=headers, json=data)
        r_ios = requests.post(ios_url, headers=headers, json=data)
