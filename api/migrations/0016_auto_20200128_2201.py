# Generated by Django 2.2.7 on 2020-01-28 22:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0015_auto_20200105_2106"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usernotifications",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]