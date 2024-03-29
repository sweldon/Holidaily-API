# Generated by Django 3.1 on 2020-09-15 17:36

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0054_comment_parent_post"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="user_likes",
            field=models.ManyToManyField(
                related_name="liked_user", to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
