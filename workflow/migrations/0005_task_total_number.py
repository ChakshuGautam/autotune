# Generated by Django 4.2.11 on 2024-04-08 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0004_task_dataset_task_parent_task_task_temp_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='total_number',
            field=models.IntegerField(default=1),
        ),
    ]