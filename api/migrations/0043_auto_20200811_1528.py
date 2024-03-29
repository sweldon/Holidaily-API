# Generated by Django 2.2.7 on 2020-08-11 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0042_auto_20200805_2132"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="emails_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="holiday",
            name="image",
            field=models.TextField(
                help_text="Paste in URL to image for upload", null=True
            ),
        ),
    ]
