# Generated by Django 2.2.7 on 2019-12-24 04:29

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_holiday"),
    ]

    operations = [
        migrations.AddField(
            model_name="holiday",
            name="date",
            field=models.DateField(
                default=datetime.datetime(2019, 12, 24, 4, 29, 35, 1753)
            ),
            preserve_default=False,
        ),
    ]
