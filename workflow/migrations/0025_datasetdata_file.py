# Generated by Django 4.2.13 on 2024-05-30 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0024_mlmodel_label_studio_comp_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="datasetdata",
            name="file",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]