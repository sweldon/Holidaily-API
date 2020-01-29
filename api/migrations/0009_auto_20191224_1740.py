# Generated by Django 2.2.7 on 2019-12-24 17:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_auto_20191224_0522"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="device_id",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="premium_id",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="premium_state",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="premium_token",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="profile_image",
            field=models.TextField(blank=True, null=True),
        ),
    ]