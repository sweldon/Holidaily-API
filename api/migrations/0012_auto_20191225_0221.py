# Generated by Django 2.2.7 on 2019-12-25 02:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0011_usercommentvotes_userholidayvotes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usercommentvotes",
            name="choice",
            field=models.IntegerField(
                choices=[
                    (0, "down"),
                    (1, "up"),
                    (2, "neutral_from_down"),
                    (3, "neutral_from_up"),
                    (4, "up_from_down"),
                    (5, "down_from_up"),
                ]
            ),
        ),
        migrations.AlterField(
            model_name="userholidayvotes",
            name="choice",
            field=models.IntegerField(
                choices=[
                    (0, "down"),
                    (1, "up"),
                    (2, "neutral_from_down"),
                    (3, "neutral_from_up"),
                    (4, "up_from_down"),
                    (5, "down_from_up"),
                ]
            ),
        ),
    ]
