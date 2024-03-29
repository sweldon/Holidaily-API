# Generated by Django 3.1 on 2020-08-21 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0045_auto_20200812_0857"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="ad_last_watched",
            field=models.DateTimeField(
                blank=True,
                help_text="Last time the user watched a reward ad",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="requested_confetti_alert",
            field=models.BooleanField(default=False),
        ),
    ]
