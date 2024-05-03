from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import User, WorkflowConfig, Workflows
from workflow.serializers import (
    PromptSerializer,
    WorkflowConfigSerializer,
    WorkflowDetailSerializer,
    WorkflowSerializer,
)
from workflow.utils import create_pydantic_model
from workflow.views import generate_task, iterate_workflow

from .mixins import UserIDMixin


class WorkflowListView(UserIDMixin, APIView):
    """
    List all workflows or create a new workflow.
    """

    def get(self, request, *args, **kwargs):
        workflows = Workflows.objects.all()
        serializer = WorkflowDetailSerializer(workflows, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = WorkflowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.META["user"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkflowDetailView(UserIDMixin, APIView):
    """
    Retrieve, update, or delete a workflow instance.
    """

    def get(self, request, workflow_id, *args, **kwargs):
        workflow = get_object_or_404(Workflows, workflow_id=workflow_id)
        serializer = WorkflowDetailSerializer(workflow)
        return Response(serializer.data)

    def put(self, request, workflow_id, *args, **kwargs):
        workflow = get_object_or_404(Workflows, workflow_id=workflow_id)
        serializer = WorkflowSerializer(workflow, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, workflow_id, *args, **kwargs):
        workflow = get_object_or_404(Workflows, workflow_id=workflow_id)
        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class WorkflowConfigCreateView(UserIDMixin, APIView):
    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            user: User = request.META["user"]

            config_data = request.data.get("config", {})

            if "schema_example" not in config_data:
                return Response(
                    {"message": "Schema Example is required!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if "config_name" in config_data:
                config_data["name"] = config_data.pop("config_name")

            Model, model_string = create_pydantic_model(config_data["schema_example"])
            field_names = list(Model.__fields__.keys())
            field_info = list(Model.__fields__.values())

            fields = [
                {name: info.annotation.__name__}
                for name, info in zip(field_names, field_info)
            ]

            combined_config_data = {
                "model_string": model_string,
                "fields": fields,
                **config_data,  # Ensure other fields are included
            }

            workflow_config_serializer = WorkflowConfigSerializer(
                data=combined_config_data
            )
            if workflow_config_serializer.is_valid():
                workflow_config: WorkflowConfig = workflow_config_serializer.save()
            else:
                return Response(
                    workflow_config_serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            workflow_data = request.data.get("workflow", {})

            if "user_prompt" in workflow_data:
                user_prompt = workflow_data.pop("user_prompt")
            else:
                return Response(
                    {"message": "User Prompt is required!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            workflow_data["user"] = user.user_id
            workflow_data["workflow_config"] = workflow_config.id

            workflow_serializer = WorkflowSerializer(data=workflow_data)
            if workflow_serializer.is_valid():
                workflow: Workflows = workflow_serializer.save()

            else:
                return Response(
                    workflow_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

            prompt_data = {
                "user_prompt": user_prompt,
                "system_prompt": workflow_config.system_prompt,
                "workflow": workflow.workflow_id,
            }

            prompt_serializer = PromptSerializer(data=prompt_data)

            if prompt_serializer.is_valid():
                prompt_serializer.save()
            else:
                return Response(
                    prompt_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

            workflow_complete_data = WorkflowDetailSerializer(workflow).data

            return Response(
                {
                    "workflow": workflow_complete_data,
                    "config": workflow_config_serializer.data,
                    "prompt": prompt_data,
                },
                status=status.HTTP_201_CREATED,
            )


@method_decorator(csrf_exempt, name="dispatch")
class WorkflowIterateView(UserIDMixin, APIView):
    def post(self, request, workflow_id):
        http_request = request._request
        return iterate_workflow(http_request, workflow_id)


@method_decorator(csrf_exempt, name="dispatch")
class WorkflowGenerateView(UserIDMixin, APIView):
    def post(self, request, workflow_id):
        http_request = request._request
        return generate_task(http_request, workflow_id)
