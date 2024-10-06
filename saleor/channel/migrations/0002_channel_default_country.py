# Generated by Django 3.2.6 on 2021-08-19 11:08

import django_countries.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("channel", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="channel",
            name="default_country",
            field=django_countries.fields.CountryField(max_length=2, null=True),
        ),
    ]
