# Generated by Django 2.2.7 on 2020-07-29 19:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0038_comment_edited"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usernotifications",
            name="title",
            field=models.CharField(max_length=150),
        ),
    ]