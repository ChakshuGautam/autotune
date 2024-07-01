# Generated by Django 4.2.13 on 2024-07-01 04:53

import django.core.validators
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0026_alter_workflows_llm_model_alter_workflows_split_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MLModelConfig",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("model_save_path", models.TextField()),
                ("dataset_path", models.TextField()),
                ("type", models.CharField(max_length=255)),
                ("system_prompt", models.TextField()),
                ("user_prompt_template", models.TextField()),
                ("schema_example", models.JSONField(default=dict)),
                (
                    "temperature",
                    models.IntegerField(
                        default=1,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(2),
                        ],
                    ),
                ),
                ("model_string", models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name="workflows",
            name="llm_model",
            field=models.CharField(
                choices=[
                    ("gpt-4-turbo", "gpt-4-turbo"),
                    ("gpt-4-turbo-preview", "gpt-4-turbo-preview"),
                    ("gpt-4o", "gpt-4o"),
                    ("gpt-4-0125-preview", "gpt-4-0125-preview"),
                    ("gpt-4-1106-preview", "gpt-4-1106-preview"),
                    ("gpt-4-vision-preview", "gpt-4-vision-preview"),
                    ("gpt-3.5-turbo-1106", "gpt-3.5-turbo-1106"),
                    ("gpt-3.5-turbo-0613", "gpt-3.5-turbo-0613"),
                    ("gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-16k-0613"),
                    ("gpt-3.5-turbo-0125", "gpt-3.5-turbo-0125"),
                    ("gpt-3.5-turbo-0301", "gpt-3.5-turbo-0301"),
                    ("gpt-3.5-turbo", "gpt-3.5-turbo"),
                ],
                default="gpt-3.5-turbo",
                max_length=255,
            ),
        ),
    ]