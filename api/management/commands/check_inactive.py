from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from datetime import timedelta
from django.utils import timezone
from api.models import Holiday
from django.contrib.auth.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        tomorrow = timezone.now().date() + timedelta(days=1)
        actives = Holiday.objects.filter(date=tomorrow, active=True).count()
        admins = list(
            User.objects.filter(is_staff=True).values_list("email", flat=True)
        )
        if actives == 0:
            mail_subject = "No Active Holidays Tomorrow"
            message = f"""
            Just a warning that there are no holidays set up for tomorrow.
            <a href="https://holidailyapp.com/admin/api/holiday/?q={tomorrow}">
            Click here to set them up!
            </a>
            """
            email = EmailMessage(mail_subject, message, to=admins)
            email.content_subtype = "html"
            email.send(fail_silently=False)
