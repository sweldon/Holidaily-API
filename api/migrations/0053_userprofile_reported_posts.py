# Generated by Django 3.1 on 2020-09-11 12:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0052_auto_20200908_1039"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="reported_posts",
            field=models.ManyToManyField(
                blank=True, related_name="reported_posts", to="api.Post"
            ),
        ),
    ]
