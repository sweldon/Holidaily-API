# Generated by Django 3.1 on 2020-11-05 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0002_auto_20201105_1103"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="featured",
            field=models.BooleanField(default=False),
        ),
    ]
