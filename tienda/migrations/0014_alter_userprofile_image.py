# Generated by Django 5.0.7 on 2025-04-04 05:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tienda", "0013_alter_productimage_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="image",
            field=models.URLField(blank=True, null=True),
        ),
    ]
