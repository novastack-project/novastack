import json
import os
import uuid
from typing import Any

import certifi
from novastack.core.bridge.pydantic import PrivateAttr, SecretStr
from novastack.core.observability import PromptObservability
from novastack.core.observability.types import PayloadRecord
from novastack.core.prompts import PromptTemplate
from novastack.observability.watsonx.supporting_classes.clients import (
    AIGovFactsClientFactory,
    WMLClientFactory,
    WosClientFactory,
)
from novastack.observability.watsonx.supporting_classes.credentials import (
    CloudPakforDataCredentials,
)
from novastack.observability.watsonx.supporting_classes.enums import Region, TaskType
from novastack.observability.watsonx.utils.data_utils import validate_and_filter_dict
from novastack.observability.watsonx.utils.instrumentation import suppress_output

os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


def _convert_payload_format(
    records: list[dict],
    feature_fields: list[str],
) -> list[dict]:
    payload_data = []
    response_fields = ["generated_text", "input_token_count", "generated_token_count"]

    for record in records:
        request = {"parameters": {"template_variables": {}}}
        results = {}

        request["parameters"]["template_variables"] = {
            field: str(record.get(field, "")) for field in feature_fields
        }

        results = {
            field: record.get(field) for field in response_fields if record.get(field)
        }

        pl_record = {
            "request": request,
            "response": {"results": [results]},
            "scoring_id": str(uuid.uuid4()),
        }

        if "response_time" in record:
            pl_record["response_time"] = record["response_time"]

        payload_data.append(pl_record)

    return payload_data


class WatsonxExternalPromptMonitor(PromptObservability):
    """
    Provides functionality to interact with IBM watsonx.governance for monitoring prompts executed on external LLMs.

    Note:
        One of the following parameters is required to create a prompt monitor:
        `project_id` or `space_id`, but not both.

    Attributes:
        api_key (str): The API key for IBM watsonx.governance.
        space_id (str, optional): The space ID in watsonx.governance.
        project_id (str, optional): The project ID in watsonx.governance.
        region (Region, optional): The region where watsonx.governance is hosted when using IBM Cloud.
            Defaults to `us-south`.
        cpd_creds (CloudPakforDataCredentials, optional): The Cloud Pak for Data environment credentials.
        subscription_id (str, optional): The subscription ID associated with the records being logged.
        service_instance_id (str, optional): The service instance ID.

    Example:
        ```python
        from novastack.observability.watsonx.supporting_classes.enums import Region

        from novastack.observability.watsonx import (
            WatsonxExternalPromptMonitor,
            CloudPakforDataCredentials,
        )

        # watsonx.governance (IBM Cloud)
        wxgov_client = WatsonxExternalPromptMonitor(
            api_key="API_KEY", space_id="SPACE_ID", region=Region.US_SOUTH
        )

        # watsonx.governance (CP4D)
        cpd_creds = CloudPakforDataCredentials(
            url="CPD_URL",
            username="USERNAME",
            password="PASSWORD",
            version="5.2",
            instance_id="openshift",
        )

        wxgov_client = WatsonxExternalPromptMonitor(
            space_id="SPACE_ID", cpd_creds=cpd_creds
        )
        ```
    """

    api_key: SecretStr | None = None
    space_id: str | None = None
    project_id: str | None = None
    region: Region | str = Region.US_SOUTH
    cpd_creds: CloudPakforDataCredentials | dict | None = None
    subscription_id: str | None = None
    service_instance_id: str | None = None

    _wos_client: Any | None = PrivateAttr(default=None)
    _container_id: str | None = PrivateAttr(default=None)
    _container_type: str | None = PrivateAttr(default=None)
    _deployment_stage: str | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:  # noqa: PYI063
        """Initialize computed fields after Pydantic validation."""
        self.region = Region.from_value(self.region)

        # Set container-related attributes
        self._container_id = self.space_id if self.space_id else self.project_id
        self._container_type = "space" if self.space_id else "project"
        self._deployment_stage = "production" if self.space_id else "development"

    def _create_detached_prompt(
        self,
        detached_details: dict,
        prompt_template_details: dict,
        detached_asset_details: dict,
    ) -> str:
        from ibm_aigov_facts_client import (  # type: ignore
            DetachedPromptTemplate,
            PromptTemplate,
        )

        aigov_client = AIGovFactsClientFactory.create_client(
            api_key=self.api_key,
            container_id=self._container_id,
            container_type=self._container_type,
            region=self.region,
            cpd_creds=self.cpd_creds,
        )

        created_detached_pta = aigov_client.assets.create_detached_prompt(
            **detached_asset_details,
            prompt_details=PromptTemplate(**prompt_template_details),
            detached_information=DetachedPromptTemplate(**detached_details),
        )

        return created_detached_pta.to_dict()["asset_id"]

    def _delete_detached_prompt(self, detached_pta_id: str) -> None:
        aigov_client = AIGovFactsClientFactory.create_client(
            api_key=self.api_key,
            container_id=self._container_id,
            container_type=self._container_type,
            region=self.region,
            cpd_creds=self.cpd_creds,
        )

        suppress_output(aigov_client.assets.delete_prompt_asset, detached_pta_id)

    def _create_deployment_pta(self, asset_id: str, name: str, model_id: str) -> str:
        wml_client = WMLClientFactory.create_client(
            api_key=self.api_key,
            region=self.region,
            cpd_creds=self.cpd_creds,
            space_id=self.space_id,
        )

        meta_props = {
            wml_client.deployments.ConfigurationMetaNames.PROMPT_TEMPLATE: {
                "id": asset_id,
            },
            wml_client.deployments.ConfigurationMetaNames.DETACHED: {},
            wml_client.deployments.ConfigurationMetaNames.NAME: name
            + " "
            + "deployment",
            wml_client.deployments.ConfigurationMetaNames.BASE_MODEL_ID: model_id,
        }

        created_deployment = wml_client.deployments.create(asset_id, meta_props)

        return wml_client.deployments.get_uid(created_deployment)

    def _delete_deployment_pta(self, deployment_id: str) -> None:
        wml_client = WMLClientFactory.create_client(
            api_key=self.api_key,
            region=self.region,
            cpd_creds=self.cpd_creds,
            space_id=self.space_id,
        )

        suppress_output(wml_client.deployments.delete, deployment_id)

    def create_prompt_monitor(
        self,
        name: str,
        model_id: str,
        task_id: TaskType | str,
        detached_model_provider: str,
        description: str = "",
        model_parameters: dict | None = None,
        detached_model_name: str | None = None,
        detached_model_url: str | None = None,
        detached_prompt_url: str | None = None,
        detached_prompt_additional_info: dict | None = None,
        prompt_template: PromptTemplate | str | None = None,
        prompt_variables: list[str] | None = None,
        locale: str = "en",
        context_fields: list[str] | None = None,
        question_field: str | None = None,
    ) -> dict:
        """
        Creates a detached (external) prompt template asset and attaches a monitor to the specified prompt template asset.

        Args:
            name (str): The name of the External Prompt Template Asset.
            model_id (str): The ID of the model associated with the prompt.
            task_id (TaskType): The task identifier.
            detached_model_provider (str): The external model provider.
            description (str, optional): A description of the External Prompt Template Asset.
            model_parameters (dict, optional): Model parameters and their respective values.
            detached_model_name (str, optional): The name of the external model.
            detached_model_url (str, optional): The URL of the external model.
            detached_prompt_url (str, optional): The URL of the external prompt.
            detached_prompt_additional_info (dict, optional): Additional information related to the external prompt.
            prompt_template (PromptTemplate, optional): The prompt template.
            prompt_variables (list[str], optional): Values for the prompt variables.
            locale (str, optional): Locale code for the input/output language. eg. "en", "pt", "es".
            context_fields (list[str], optional): A list of fields that will provide context to the prompt.
                Applicable only for "retrieval_augmented_generation" task type.
            question_field (str, optional): The field containing the question to be answered.
                Applicable only for "retrieval_augmented_generation" task type.

        Example:
            ```python
            from novastack.observability.watsonx.supporting_classes.enums import TaskType

            wxgov_client.create_prompt_monitor(
                name="Detached prompt (model AWS Anthropic)",
                model_id="anthropic.claude-v2",
                task_id=TaskType.RETRIEVAL_AUGMENTED_GENERATION,
                detached_model_provider="AWS Bedrock",
                detached_model_name="Anthropic Claude 2.0",
                detached_model_url="https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html",
                prompt_template="You are a helpful AI assistant that provides clear and accurate answers. {context}. Question: {input_query}.",
                prompt_variables=["context", "input_query"],
                context_fields=["context"],
                question_field="input_query",
            )
            ```
        """
        task_id = TaskType.from_value(task_id).value
        rollback_stack = []

        prompt_template = PromptTemplate.from_value(prompt_template)

        if (not (self.project_id or self.space_id)) or (
            self.project_id and self.space_id
        ):
            raise ValueError(
                "Invalid configuration: Neither was provided: please set either 'project_id' or 'space_id'. "
                "Both were provided: 'project_id' and 'space_id' cannot be set at the same time."
            )

        if task_id == TaskType.RETRIEVAL_AUGMENTED_GENERATION.value:
            if not context_fields or not question_field:
                raise ValueError(
                    "For 'retrieval_augmented_generation' task, requires non-empty 'context_fields' and 'question_field'."
                )

        prompt_metadata = locals()
        # Remove unused vars from dict
        prompt_metadata.pop("self", None)
        prompt_metadata.pop("context_fields", None)
        prompt_metadata.pop("question_field", None)
        prompt_metadata.pop("locale", None)

        # Update name of keys to aigov_facts api
        prompt_metadata["input"] = getattr(
            prompt_metadata.pop("prompt_template", None), "template", None
        )
        prompt_metadata["model_provider"] = prompt_metadata.pop(
            "detached_model_provider",
            None,
        )
        prompt_metadata["model_name"] = prompt_metadata.pop("detached_model_name", None)
        prompt_metadata["model_url"] = prompt_metadata.pop("detached_model_url", None)
        prompt_metadata["prompt_url"] = prompt_metadata.pop("detached_prompt_url", None)
        prompt_metadata["prompt_additional_info"] = prompt_metadata.pop(
            "detached_prompt_additional_info",
            None,
        )

        # Update list of vars to dict
        prompt_metadata["prompt_variables"] = dict.fromkeys(
            prompt_metadata["prompt_variables"], ""
        )

        if not self._wos_client:
            self._wos_client = WosClientFactory.create_client(
                api_key=self.api_key,
                region=self.region,
                cpd_creds=self.cpd_creds,
                service_instance_id=self.service_instance_id,
            )

        detached_details = validate_and_filter_dict(
            prompt_metadata,
            ["model_name", "model_url", "prompt_url", "prompt_additional_info"],
            ["model_id", "model_provider"],
        )
        detached_details["prompt_id"] = "detached_prompt_" + str(uuid.uuid4())

        prompt_details = validate_and_filter_dict(
            prompt_metadata,
            ["prompt_variables", "input", "model_parameters"],
        )

        detached_asset_details = validate_and_filter_dict(
            prompt_metadata,
            ["description"],
            ["name", "model_id", "task_id"],
        )

        detached_pta_id = suppress_output(
            self._create_detached_prompt,
            detached_details,
            prompt_details,
            detached_asset_details,
        )
        rollback_stack.append(lambda: self._delete_detached_prompt(detached_pta_id))

        deployment_id = None
        if self._container_type == "space":
            deployment_id = suppress_output(
                self._create_deployment_pta, detached_pta_id, name, model_id
            )
            rollback_stack.append(lambda: self._delete_deployment_pta(deployment_id))

        monitors = {
            "generative_ai_quality": {
                "parameters": {"min_sample_size": 10, "metrics_configuration": {}},
            },
        }

        max_attempt_execute_prompt_setup = 0
        while max_attempt_execute_prompt_setup < 2:
            try:
                generative_ai_monitor_details = suppress_output(
                    self._wos_client.wos.execute_prompt_setup,
                    prompt_template_asset_id=detached_pta_id,
                    space_id=self.space_id,
                    project_id=self.project_id,
                    deployment_id=deployment_id,
                    label_column="reference_output",
                    context_fields=context_fields,
                    question_field=question_field,
                    operational_space_id=self._deployment_stage,
                    problem_type=task_id,
                    data_input_locale=[locale],
                    generated_output_locale=[locale],
                    input_data_type="unstructured_text",
                    supporting_monitors=monitors,
                    background_mode=False,
                )

                break

            except Exception as e:
                if (
                    e.code == 403
                    and "The user entitlement does not exist" in e.message
                    and max_attempt_execute_prompt_setup < 1
                ):
                    max_attempt_execute_prompt_setup = (
                        max_attempt_execute_prompt_setup + 1
                    )

                    data_marts = self._wos_client.data_marts.list().result
                    if (data_marts.data_marts is None) or (not data_marts.data_marts):
                        raise ValueError(
                            "Error retrieving IBM watsonx.governance (openscale) data mart. \
                                         Make sure the data mart are configured.",
                        )

                    data_mart_id = data_marts.data_marts[0].metadata.id

                    self._wos_client.wos.add_instance_mapping(
                        service_instance_id=data_mart_id,
                        space_id=self.space_id,
                        project_id=self.project_id,
                    )
                else:
                    max_attempt_execute_prompt_setup = 2
                    raise

        generative_ai_monitor_details = generative_ai_monitor_details.result._to_dict()

        wos_status = generative_ai_monitor_details.get("status", {})
        if wos_status.get("state") == "ERROR":
            for rollback_step in reversed(rollback_stack):
                rollback_step()
            raise Exception(wos_status.get("failure"))

        return {
            "detached_prompt_template_asset_id": detached_pta_id,
            "deployment_id": deployment_id,
            "subscription_id": generative_ai_monitor_details.get(
                "subscription_id", None
            ),
        }

    def store_payload_records(
        self,
        request_records: list[dict],
        subscription_id: str | None = None,
    ) -> list[str]:
        """
        Stores records to the payload logging system.

        Args:
            request_records (list[dict]): A list of records to be logged, where each record is represented as a dictionary.
            subscription_id (str, optional): The subscription ID associated with the records being logged.

        Example:
            ```python
            wxgov_client.store_payload_records(
                request_records=[
                    {
                        "context1": "value_context1",
                        "context2": "value_context2",
                        "input_query": "What's novastack Framework?",
                        "generated_text": "novastack is a data framework to make AI easier to work with.",
                        "input_token_count": 25,
                        "generated_token_count": 150,
                    }
                ],
                subscription_id="5d62977c-a53d-4b6d-bda1-7b79b3b9d1a0",
            )
            ```
        """
        from ibm_watson_openscale.supporting_classes.enums import (
            DataSetTypes,
            TargetTypes,
        )

        # Expected behavior: Prefer using fn `subscription_id`.
        # Fallback to `self.subscription_id` if `subscription_id` None or empty.
        _subscription_id = subscription_id or self.subscription_id

        if _subscription_id is None or _subscription_id == "":
            raise ValueError(
                "Unexpected value for 'subscription_id': Cannot be None or empty string."
            )

        if not self._wos_client:
            self._wos_client = WosClientFactory.create_client(
                api_key=self.api_key,
                region=self.region,
                cpd_creds=self.cpd_creds,
                service_instance_id=self.service_instance_id,
            )

        subscription_details = self._wos_client.subscriptions.get(
            _subscription_id,
        ).result
        subscription_details = json.loads(str(subscription_details))

        feature_fields = subscription_details["entity"]["asset_properties"][
            "feature_fields"
        ]

        payload_data_set_id = (
            self._wos_client.data_sets.list(
                type=DataSetTypes.PAYLOAD_LOGGING,
                target_target_id=_subscription_id,
                target_target_type=TargetTypes.SUBSCRIPTION,
            )
            .result.data_sets[0]
            .metadata.id
        )

        payload_data = _convert_payload_format(request_records, feature_fields)

        suppress_output(
            self._wos_client.data_sets.store_records,
            data_set_id=payload_data_set_id,
            request_body=payload_data,
            background_mode=False,
        )

        return [data["scoring_id"] + "-1" for data in payload_data]

    def store_feedback_records(
        self,
        request_records: list[dict],
        subscription_id: str | None = None,
    ) -> dict:
        """
        Stores records to the feedback logging system.

        Info:
            - Feedback data for external prompt **must include** the model output named `generated_text`.
            - For prompt monitors created using novastack, the label field is `reference_output`.

        Args:
            request_records (list[dict]): A list of records to be logged, where each record is represented as a dictionary.
            subscription_id (str, optional): The subscription ID associated with the records being logged.

        Example:
            ```python
            wxgov_client.store_feedback_records(
                request_records=[
                    {
                        "context1": "value_context1",
                        "context2": "value_context2",
                        "input_query": "What's novastack Framework?",
                        "reference_output": "novastack is a data framework to make AI easier to work with."
                        "generated_text": "novastack is a data framework to make AI easier to work with.",
                    }
                ],
                subscription_id="5d62977c-a53d-4b6d-bda1-7b79b3b9d1a0",
            )
            ```
        """
        from ibm_watson_openscale.supporting_classes.enums import (
            DataSetTypes,
            TargetTypes,
        )

        # Expected behavior: Prefer using fn `subscription_id`.
        # Fallback to `self.subscription_id` if `subscription_id` None or empty.
        _subscription_id = subscription_id or self.subscription_id

        if _subscription_id is None or _subscription_id == "":
            raise ValueError(
                "Unexpected value for 'subscription_id': Cannot be None or empty string."
            )

        if not self._wos_client:
            self._wos_client = WosClientFactory.create_client(
                api_key=self.api_key,
                region=self.region,
                cpd_creds=self.cpd_creds,
                service_instance_id=self.service_instance_id,
            )

        subscription_details = self._wos_client.subscriptions.get(
            _subscription_id,
        ).result
        subscription_details = json.loads(str(subscription_details))

        feature_fields = subscription_details["entity"]["asset_properties"][
            "feature_fields"
        ]

        # Rename generated_text to _original_prediction (expected by WOS feedback dataset)
        # Validate required fields for detached/external monitor
        for i, d in enumerate(request_records):
            d["_original_prediction"] = d.pop("generated_text", None)
            request_records[i] = validate_and_filter_dict(
                d, feature_fields, ["_original_prediction"]
            )

        feedback_data_set_id = (
            self._wos_client.data_sets.list(
                type=DataSetTypes.FEEDBACK,
                target_target_id=_subscription_id,
                target_target_type=TargetTypes.SUBSCRIPTION,
            )
            .result.data_sets[0]
            .metadata.id
        )

        suppress_output(
            self._wos_client.data_sets.store_records,
            data_set_id=feedback_data_set_id,
            request_body=request_records,
            background_mode=False,
        )

        return {"status": "success"}

    def __call__(self, payload: PayloadRecord) -> None:
        self.store_payload_records(
            [
                {
                    **payload.prompt_variable_values,
                    **payload.model_dump(
                        exclude_none=True,
                        exclude={"system_prompt", "prompt_variable_values"},
                    ),
                }
            ]
        )
