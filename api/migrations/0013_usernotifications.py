# Generated by Django 2.2.7 on 2019-12-25 02:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0012_auto_20191225_0221"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserNotifications",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("notification_id", models.IntegerField()),
                (
                    "notification_type",
                    models.IntegerField(choices=[(0, "comment"), (1, "news")]),
                ),
                ("read", models.BooleanField(default=False)),
                ("content", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("title", models.CharField(max_length=50)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
