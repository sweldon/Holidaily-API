# Generated by Django 2.2.7 on 2020-04-18 16:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0032_userprofile_platform"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usernotifications",
            name="notification_type",
            field=models.IntegerField(
                choices=[(0, "comment"), (1, "news"), (2, "holiday")]
            ),
        ),
    ]
