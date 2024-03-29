# Generated by Django 2.2.7 on 2020-04-07 10:38

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0029_auto_20200406_1932"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="blocked_users",
            field=models.ManyToManyField(
                blank=True,
                null=True,
                related_name="blocked_users",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="reported_comments",
            field=models.ManyToManyField(
                blank=True,
                null=True,
                related_name="reported_comments",
                to="api.Comment",
            ),
        ),
    ]
