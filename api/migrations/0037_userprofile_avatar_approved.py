# Generated by Django 2.2.7 on 2020-05-05 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0036_userprofile_last_launched"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="avatar_approved",
            field=models.BooleanField(default=False),
        ),
    ]