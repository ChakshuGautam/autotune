import io
import json
import os
import shutil

from celery import shared_task
from celery.utils.log import get_task_logger
from datasets import load_dataset
from django.conf import settings
from django.utils import timezone
from huggingface_hub import HfApi, login
from transformers import TrainerCallback

from workflow.models import MLModel, Task, TrainingMetadata, User

from .tasks import get_task_class

logger = get_task_logger(__name__)

from .tasks import get_task_class

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=settings.CELERY_MAX_RETRIES, retry_backoff=True)
def train(self, req_data, user_id, training_task):
    task_id = self.request.id
    task = Task.objects.get(id=task_id)
    task.status = "TRAINING"
    task.save()
    meta = train_model(self, req_data, task_id)
    task.status = "PUSHING"
    task.save()
    try:
        huggingface_id = req_data.get("save_path").split("/")[0]
        model_name = req_data.get("save_path").split("/")[-1]

        model_id = req_data.get("model_id")
        if model_id:
            # Check if the model exists
            try:
                ml_model = MLModel.objects.get(id=model_id)
                # Update the model if it exists
                ml_model.name = model_name
                ml_model.is_trained_at_autotune = True
                ml_model.is_locally_cached = True
                ml_model.uploaded_at = timezone.now()
                ml_model.latest_commit_hash = meta.get("latest_commit_hash")
                ml_model.huggingface_id = huggingface_id
                ml_model.save()
                logger.info(f"Updated MLModel with ID {model_id}")
            except MLModel.DoesNotExist:
                logger.error(f"MLModel with ID {model_id} does not exist.")
                return  # Optionally, you can handle this case differently
        else:
            ml_model = MLModel.objects.create(
                name=model_name,
                is_trained_at_autotune=True,
                is_locally_cached=True,
                uploaded_at=timezone.now(),
                latest_commit_hash=meta.get("latest_commit_hash"),
                huggingface_id=huggingface_id,
            )
            logger.info("Created a new MLModel")
        user = User.objects.get(user_id=user_id)

        TrainingMetadata.objects.create(
            model=ml_model, logs=meta["logs"], metrics=meta["metrics"], user=user
        )
        logger.info("Created TrainingMetadata")
    except Exception as e:
        logger.error(f"Failed to update model and log: {str(e)}")

    task.status = "COMPLETE"
    task.save()


class CeleryProgressCallback(TrainerCallback):
    def __init__(self, task):
        self.task = task

    def on_log(self, args, state, control, logs, **kwargs):
        self.task.update_state(state="TRAINING", meta=state.log_history)


def train_model(celery, req_data, task_id):
    task_class = get_task_class(req_data["task"])
    dataset = load_dataset(req_data["dataset"]).shuffle()
    task = task_class(req_data["model"], dataset, req_data["version"])

    api_key = settings.HUGGING_FACE_TOKEN

    training_args = task.TrainingArguments(
        output_dir=f"./results_{task_id}",
        num_train_epochs=req_data["epochs"],
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        logging_dir=f"./logs_{task_id}",
        save_strategy="epoch",
        evaluation_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        warmup_steps=500,
        weight_decay=0.01,
        do_predict=True,
    )

    trainer = task.Trainer(
        model=task.model, args=training_args, callbacks=[CeleryProgressCallback(celery)]
    )

    trainer.train()

    _, _, metrics = trainer.predict(task.tokenized_dataset["test"])
    json_metrics = json.dumps(metrics)
    json_bytes = json_metrics.encode("utf-8")
    fileObj = io.BytesIO(json_bytes)

    meta = {"logs": trainer.state.log_history, "metrics": metrics}
    celery.update_state(state="PUSHING", meta=meta)

    login(token=api_key)
    trainer.model.push_to_hub(
        req_data["save_path"], commit_message="pytorch_model.bin upload/update"
    )
    trainer.tokenizer.push_to_hub(req_data["save_path"])

    # quantized_model = quantize_dynamic(task.model, {torch.nn.Linear}, dtype=torch.qint8)

    # ort_model = task.onnx.from_pretrained(
    #     task.model, export=True
    # )  # revision = req['version']
    # ort_model.save_pretrained(f"./results_{celery.request.id}/onnx")
    # ort_model.push_to_hub(
    #     f"./results_{celery.request.id}/onnx",
    #     repository_id=req_data["save_path"],
    #     use_auth_token=True,
    # )

    hfApi = HfApi(endpoint="https://huggingface.co", token=api_key)
    upload = hfApi.upload_file(
        path_or_fileobj=fileObj,
        path_in_repo="metrics.json",
        repo_id=req_data["save_path"],
        repo_type="model",
    )

    meta["latest_commit_hash"] = upload.commit_url.split("/")[-1]

    if os.path.exists(f"./results_{celery.request.id}"):
        shutil.rmtree(f"./results_{celery.request.id}")
    if os.path.exists(f"./logs_{celery.request.id}"):
        shutil.rmtree(f"./logs_{celery.request.id}")

    logger.info("Training complete")

    return meta