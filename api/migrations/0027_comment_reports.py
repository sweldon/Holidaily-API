# Generated by Django 2.2.7 on 2020-04-06 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0026_holiday_created"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment", name="reports", field=models.IntegerField(default=0),
        ),
    ]
