from datetime import timedelta

from django import template
from django.urls import reverse
from django.utils import timezone

register = template.Library()


@register.simple_tag
def generate_tomorrow_link(obj):
    tomorrow = timezone.now().date() + timedelta(days=1)
    holidays = reverse("admin:api_holiday_changelist")
    return f"{holidays}?q={tomorrow}"


@register.simple_tag
def generate_today_link(obj):
    today = timezone.now().date()
    holidays = reverse("admin:api_holiday_changelist")
    return f"{holidays}?q={today}"
