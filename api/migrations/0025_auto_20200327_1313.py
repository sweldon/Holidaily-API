# Generated by Django 2.2.7 on 2020-03-27 13:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0024_comment_deleted"),
    ]

    operations = [
        migrations.AddField(
            model_name="holiday",
            name="image_format",
            field=models.CharField(
                choices=[("jpeg", "jpeg"), ("png", "png")],
                default="jpeg",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="holiday",
            name="image_name",
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
    ]