# Generated by Django 2.2.7 on 2020-03-21 13:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0022_auto_20200316_2208"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="logged_out",
            field=models.BooleanField(default=False),
        ),
    ]
