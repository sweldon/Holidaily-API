"""Temporary one-off to set up image names"""

from django.core.management.base import BaseCommand
from api.models import Holiday
from holidaily.settings import (
    HOLIDAY_IMAGE_WIDTH,
    HOLIDAY_IMAGE_HEIGHT,
)
from api.constants import CLOUDFRONT_DOMAIN
import requests
from PIL import Image
from io import BytesIO
import boto3


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Go through all holidays and update their image name, to be used by serializer
        all_holidays = Holiday.objects.all()
        for h in all_holidays:
            if not h.image_name:
                h.image_name = f"{h.name.strip().replace(' ', '-')}.{h.image_format}"
                h.save()

        # Make sure the non-s3-linked ones have a source in s3. Update the image URL just so we can check,
        # but dont need it because the serializer makes the URL to the image
        non_s3_days = Holiday.objects.all().exclude(name__icontains="holiday-images")
        print(non_s3_days.count())
        for x in non_s3_days:
            url = x.image
            file_name = f"{x.name.strip().replace(' ', '-')}.{x.image_format}"
            image_size = (HOLIDAY_IMAGE_WIDTH, HOLIDAY_IMAGE_HEIGHT)
            image_data = requests.get(url).content
            image_object = Image.open(BytesIO(image_data))
            image_object.thumbnail(image_size)
            byte_arr = BytesIO()
            image_object.save(byte_arr, format=x.image_format)
            s3_client = boto3.resource("s3")
            s3_client.Bucket("holiday-images").put_object(
                Key=file_name, Body=byte_arr.getvalue()
            )
            x.image = f"{CLOUDFRONT_DOMAIN}/{x.image_name}"
            x.save()
