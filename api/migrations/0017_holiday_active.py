# Generated by Django 2.2.7 on 2020-01-28 23:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0016_auto_20200128_2201"),
    ]

    operations = [
        migrations.AddField(
            model_name="holiday",
            name="active",
            field=models.BooleanField(default=True),
        ),
    ]
