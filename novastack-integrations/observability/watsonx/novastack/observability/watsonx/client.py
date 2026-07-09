import os
import uuid
from typing import Any

import certifi
from deprecated import deprecated
from donkey.core.bridge.pydantic import BaseModel, PrivateAttr
from donkey.core.toolkit import validate_enum
from donkey.core.toolkit.retry import retry, stop_after_attempt
from ibm_aigov_facts_client import (
    DetachedPromptTemplate,
    PromptTemplate,
)
from ibm_cloud_sdk_core.authenticators import Authenticator as IBMAuthenticator
from novastack.observability.watsonx.enums import Region, TaskType
from novastack.observability.watsonx.integrated_system import (
    IntegratedSystemCredentials,
)
from novastack.observability.watsonx.schemas import WatsonxMetricSpec
from novastack.observability.watsonx.supporting_classes.clients import (
    AIGovFactsClientFactory,
    WMLClientFactory,
    WosClientFactory,
)
from novastack.observability.watsonx.supporting_classes.custom_metrics import (
    CustomMetrics,
)
from novastack.observability.watsonx.supporting_classes.data_sets import DataSets
from novastack.observability.watsonx.supporting_classes.utils import (
    retry_if_exception_wos_entitlement,
    suppress_output,
    validate_and_filter_dict,
    validate_container_id,
)

os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


class WatsonxGovClient(BaseModel):
    """
    Unified client for interacting with IBM watsonx.governance for prompt monitoring.

    Supports both native IBM watsonx.ai LLMs (via :meth:`setup_monitor`) and
    external LLM providers (via :meth:`setup_external_monitor`).

    Note:
        One of the following parameters is required: `project_id` or `space_id`, but not both.

    Attributes:
        authenticator (IBMAuthenticator): The authenticator specifies the authentication mechanism.
        space_id (str, optional): The space ID in watsonx.governance.
        project_id (str, optional): The project ID in watsonx.governance.
        region (str, optional): The region where watsonx.governance is hosted when using IBM Cloud.
            Defaults to `us-south`.
        service_instance_id (str, optional): The service instance ID.

    Example:
        ```python
        from novastack.observability.watsonx import WatsonxGovClient
        from novastack.observability.watsonx.authenticators import IAMAuthenticator

        # watsonx.governance (IBM Cloud)
        client = WatsonxGovClient(
            authenticator=IAMAuthenticator(api_key="API_KEY"),
            region="us-south",
            space_id="SPACE_ID",
        )

        # watsonx.governance (CP4D)
        from novastack.observability.watsonx.authenticators import (
            CloudPakForDataAuthenticator,
        )

        client = WatsonxGovClient(
            authenticator=CloudPakForDataAuthenticator(
                url="CPD_URL",
                username="USERNAME",
                password="PASSWORD",
                instance_id="openshift",
                version="5.3",
            ),
            space_id="SPACE_ID",
        )
        ```
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    authenticator: IBMAuthenticator
    space_id: str | None = None
    project_id: str | None = None
    region: str = Region.US_SOUTH
    service_instance_id: str | None = None

    _container_id: str | None = PrivateAttr(default=None)
    _container_type: str | None = PrivateAttr(default=None)
    _deployment_stage: str | None = PrivateAttr(default=None)

    __aigov_client: Any | None = PrivateAttr(default=None)
    __wos_client: Any | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:  # noqa: PYI063
        self._container_id = self.space_id if self.space_id else self.project_id
        self._container_type = "space" if self.space_id else "project"
        self._deployment_stage = "production" if self.space_id else "development"

    @property
    def _aigov_client(self) -> Any:
        if self.__aigov_client is None:
            self.__aigov_client = AIGovFactsClientFactory.create_client(
                authenticator=self.authenticator,
                container_id=self._container_id,
                container_type=self._container_type,
                region=self.region,
            )
        return self.__aigov_client

    @property
    def _wos_client(self) -> Any:
        if self.__wos_client is None:
            self.__wos_client = WosClientFactory.create_client(
                authenticator=self.authenticator,
                region=self.region,
                service_instance_id=self.service_instance_id,
            )
        return self.__wos_client

    def _create_deployment_pta(self, asset_id: str, name: str, model_id: str) -> str:
        wml_client = WMLClientFactory.create_client(
            authenticator=self.authenticator,
            region=self.region,
            space_id=self.space_id,
        )

        meta_props = {
            wml_client.deployments.ConfigurationMetaNames.PROMPT_TEMPLATE: {
                "id": asset_id,
            },
            wml_client.deployments.ConfigurationMetaNames.FOUNDATION_MODEL: {},
            wml_client.deployments.ConfigurationMetaNames.NAME: f"{name} deployment",
            wml_client.deployments.ConfigurationMetaNames.BASE_MODEL_ID: model_id,
        }

        created_deployment = wml_client.deployments.create(asset_id, meta_props)

        return wml_client.deployments.get_uid(created_deployment)

    def _create_detached_prompt(
        self,
        detached_details: dict,
        prompt_template_details: dict,
        detached_asset_details: dict,
    ) -> str:
        created_detached_pta = self._aigov_client.assets.create_detached_prompt(
            **detached_asset_details,
            prompt_details=PromptTemplate(**prompt_template_details),
            detached_information=DetachedPromptTemplate(**detached_details),
        )

        return created_detached_pta.to_dict()["asset_id"]

    def _create_prompt(
        self,
        prompt_template_details: dict,
        asset_details: dict,
    ) -> str:
        created_pta = self._aigov_client.assets.create_prompt(
            **asset_details,
            input_mode="freeform",
            prompt_details=PromptTemplate(**prompt_template_details),
        )

        return created_pta.to_dict()["asset_id"]

    def _delete_deployment_pta(self, deployment_id: str) -> None:
        wml_client = WMLClientFactory.create_client(
            authenticator=self.authenticator,
            region=self.region,
            space_id=self.space_id,
        )

        suppress_output(wml_client.deployments.delete, deployment_id)

    def _delete_prompt_asset(self, asset_id: str) -> None:
        suppress_output(self._aigov_client.assets.delete_prompt_asset, asset_id)

    def _wos_execute_prompt_setup(
        self,
        pta_id: str,
        task_id: str,
        locale: str,
        context_fields: list[str] | None,
        question_field: str | None,
        deployment_id: str | None = None,
    ) -> str:
        monitors = {
            "generative_ai_quality": {
                "parameters": {"min_sample_size": 10, "metrics_configuration": {}},
            },
        }

        @retry(
            stop=stop_after_attempt(2),
            when=retry_if_exception_wos_entitlement(
                wos_client=self._wos_client,
                space_id=self.space_id,
                project_id=self.project_id,
            ),
            reraise=True,
        )
        def _execute():
            return suppress_output(
                self._wos_client.wos.execute_prompt_setup,
                prompt_template_asset_id=pta_id,
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

        generative_ai_monitor_details = _execute()

        generative_ai_monitor_details = generative_ai_monitor_details._to_dict()

        wos_status = generative_ai_monitor_details.get("status", {})

        if wos_status.get("state") == "ERROR":
            raise Exception(wos_status.get("failure"))

        return generative_ai_monitor_details.get("subscription_id", None)

    def setup_monitor(
        self,
        name: str,
        model_id: str,
        task_id: str,
        description: str = "",
        model_parameters: dict | None = None,
        prompt_template: str | None = None,
        prompt_variables: list[str] | None = None,
        locale: str = "en",
        context_fields: list[str] | None = None,
        question_field: str | None = None,
    ) -> dict:
        """
        Creates an IBM prompt template asset and setup monitor for the given prompt template asset.

        Args:
            name (str): The name of the Prompt Template Asset.
            model_id (str): The ID of the model associated with the prompt.
            task_id (str): The task identifier.
            description (str, optional): A description of the Prompt Template Asset.
            model_parameters (dict, optional): A dictionary of model parameters and their respective values.
            prompt_template (str, optional): The prompt template.
            prompt_variables (list[str], optional): A list of values for prompt input variables.
            locale (str, optional): Locale code for the input/output language. eg. "en", "pt", "es".
            context_fields (list[str], optional): A list of fields that will provide context to the prompt.
                Applicable only for the `retrieval_augmented_generation` task type.
            question_field (str, optional): The field containing the question to be answered.
                Applicable only for the `retrieval_augmented_generation` task type.

        Example:
            ```python
            client.setup_monitor(
                name="IBM prompt template",
                model_id="ibm/granite-3-2b-instruct",
                task_id="retrieval_augmented_generation",
                prompt_template="You are a helpful AI assistant. {context}. Question: {input_query}.",
                prompt_variables=["context", "input_query"],
                context_fields=["context"],
                question_field="input_query",
            )
            ```
        """
        validate_enum(task_id, "task_id", TaskType)
        validate_container_id(self.project_id, self.space_id)

        if task_id == TaskType.RETRIEVAL_AUGMENTED_GENERATION:
            if not context_fields or not question_field:
                raise ValueError(
                    "For 'retrieval_augmented_generation' task, requires non-empty 'context_fields' and 'question_field'."
                )

        prompt_metadata = {
            "name": name,
            "model_id": model_id,
            "task_id": task_id,
            "description": description,
            "model_parameters": model_parameters,
            "input": prompt_template,
            "prompt_variables": dict.fromkeys(prompt_variables, "")
            if prompt_variables
            else {},
        }

        rollback_stack = []

        prompt_details = validate_and_filter_dict(
            prompt_metadata,
            ["prompt_variables", "input", "model_parameters"],
        )

        asset_details = validate_and_filter_dict(
            prompt_metadata,
            ["description"],
            ["name", "model_id", "task_id"],
        )

        try:
            pta_id = suppress_output(self._create_prompt, prompt_details, asset_details)
            rollback_stack.append(lambda: self._delete_prompt_asset(pta_id))

            deployment_id = None
            if self._container_type == "space":
                deployment_id = suppress_output(
                    self._create_deployment_pta, pta_id, name, model_id
                )
                rollback_stack.append(
                    lambda: self._delete_deployment_pta(deployment_id)
                )

            subscription_id = self._wos_execute_prompt_setup(
                pta_id=pta_id,
                task_id=task_id,
                locale=locale,
                context_fields=context_fields,
                question_field=question_field,
                deployment_id=deployment_id,
            )

            return {
                "asset_id": pta_id,
                "asset_type": "prompt_template",
                "deployment_id": deployment_id,
                "subscription_id": subscription_id,
            }
        except Exception:
            for step in reversed(rollback_stack):
                step()
            raise

    def setup_external_monitor(
        self,
        name: str,
        model_id: str,
        model_provider: str,
        task_id: str,
        description: str = "",
        model_name: str | None = None,
        model_parameters: dict | None = None,
        model_url: str | None = None,
        prompt_id: str | None = None,
        prompt_url: str | None = None,
        prompt_additional_info: dict | None = None,
        prompt_template: str | None = None,
        prompt_variables: list[str] | None = None,
        locale: str = "en",
        context_fields: list[str] | None = None,
        question_field: str | None = None,
    ) -> dict:
        """
        Creates a detached (external) prompt template asset and attaches a monitor to it.

        Args:
            name (str): The name of the External Prompt Template Asset.
            model_id (str): The ID of the model associated with the prompt.
            model_provider (str): The model provider (e.g. "AWS Bedrock", "Azure OpenAI").
            task_id (str): The task identifier.
            description (str, optional): A description of the External Prompt Template Asset.
            model_name (str, optional): The name of the external model.
            model_parameters (dict, optional): Model parameters and their respective values.
            model_url (str, optional): The URL of the external model.
            prompt_id (str, optional): The ID of the external prompt. Auto-generated if not provided.
            prompt_url (str, optional): The URL of the external prompt.
            prompt_additional_info (dict, optional): Additional information related to the external prompt.
            prompt_template (str, optional): The prompt template.
            prompt_variables (list[str], optional): Values for the prompt variables.
            locale (str, optional): Locale code for the input/output language. eg. "en", "pt", "es".
            context_fields (list[str], optional): A list of fields that will provide context to the prompt.
                Applicable only for the `retrieval_augmented_generation` task type.
            question_field (str, optional): The field containing the question to be answered.
                Applicable only for the `retrieval_augmented_generation` task type.

        Example:
            ```python
            client.setup_external_monitor(
                name="Prompt Template for Retrieval Augmented Generation",
                model_id="anthropic.claude-v2",
                model_provider="AWS Bedrock",
                task_id="retrieval_augmented_generation",
                model_name="Anthropic Claude 2.0",
                model_url="https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html",
                prompt_template="You are a helpful AI assistant. {context}. Question: {input_query}.",
                prompt_variables=["context", "input_query"],
                context_fields=["context"],
                question_field="input_query",
            )
            ```
        """
        validate_enum(task_id, "task_id", TaskType)
        validate_container_id(self.project_id, self.space_id)

        if task_id == TaskType.RETRIEVAL_AUGMENTED_GENERATION:
            if not context_fields or not question_field:
                raise ValueError(
                    "For 'retrieval_augmented_generation' task, requires non-empty 'context_fields' and 'question_field'."
                )

        prompt_metadata = {
            "name": name,
            "model_id": model_id,
            "model_provider": model_provider,
            "task_id": task_id,
            "description": description,
            "model_name": model_name,
            "model_parameters": model_parameters,
            "model_url": model_url,
            "prompt_url": prompt_url,
            "prompt_additional_info": prompt_additional_info,
            "input": prompt_template,
            "prompt_variables": dict.fromkeys(prompt_variables, "")
            if prompt_variables
            else {},
        }

        rollback_stack = []

        detached_details = validate_and_filter_dict(
            prompt_metadata,
            ["model_name", "model_url", "prompt_url", "prompt_additional_info"],
            ["model_id", "model_provider"],
        )
        detached_details["prompt_id"] = prompt_id or str(uuid.uuid4())

        prompt_details = validate_and_filter_dict(
            prompt_metadata,
            ["prompt_variables", "input", "model_parameters"],
        )

        detached_asset_details = validate_and_filter_dict(
            prompt_metadata,
            ["description"],
            ["name", "model_id", "task_id"],
        )

        try:
            pta_id = suppress_output(
                self._create_detached_prompt,
                detached_details,
                prompt_details,
                detached_asset_details,
            )
            rollback_stack.append(lambda: self._delete_prompt_asset(pta_id))

            try:
                subscription_id = self._wos_execute_prompt_setup(
                    pta_id=pta_id,
                    task_id=task_id,
                    locale=locale,
                    context_fields=context_fields,
                    question_field=question_field,
                )
            except Exception as e:
                # Some CP4D versions require a deployment_id during subscription setup.
                # If the API returns HTTP 400 with "deployment_id missing", a deployment
                # is created for the prompt template asset before proceeding.
                if getattr(
                    e, "status_code", None
                ) == 400 and "deployment_id missing" in getattr(e, "message", ""):
                    deployment_id = None
                    if self._container_type == "space":
                        deployment_id = suppress_output(
                            self._create_deployment_pta, pta_id, name, model_id
                        )
                        rollback_stack.append(
                            lambda: self._delete_deployment_pta(deployment_id)
                        )

                    subscription_id = self._wos_execute_prompt_setup(
                        pta_id=pta_id,
                        task_id=task_id,
                        locale=locale,
                        context_fields=context_fields,
                        question_field=question_field,
                        deployment_id=deployment_id,
                    )

                else:
                    raise

            return {
                "asset_id": pta_id,
                "asset_type": "detached_prompt_template",
                "subscription_id": subscription_id,
            }
        except Exception:
            for step in reversed(rollback_stack):
                step()
            raise

    def log_payload_records(
        self,
        request_records: list[dict],
        subscription_id: str | None = None,
    ) -> list[str]:
        """
        Stores records to the payload logging system.

        Args:
            request_records (list[dict]): A list of records to be logged. Each record is represented as a dictionary.
            subscription_id (str, optional): The subscription ID associated with the records being logged.

        Example:
            ```python
            client.log_payload_records(
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
        data_sets = DataSets(wos_client=self._wos_client)

        return data_sets.store_payload_records(
            request_records=request_records,
            subscription_id=subscription_id,
        )

    def log_feedback_records(
        self,
        request_records: list[dict],
        subscription_id: str | None = None,
    ) -> dict:
        """
        Stores records to the feedback logging system.

        Info:
            - Feedback data **must include** the model output named `generated_text`.
            - For prompt monitors created using novastack, the label field is `reference_output`.

        Args:
            request_records (list[dict]): A list of records to be logged, where each record is represented as a dictionary.
            subscription_id (str, optional): The subscription ID associated with the records being logged.

        Example:
            ```python
            client.log_feedback_records(
                request_records=[
                    {
                        "context1": "value_context1",
                        "context2": "value_context2",
                        "input_query": "What's novastack Framework?",
                        "reference_output": "novastack is a data framework to make AI easier to work with.",
                        "generated_text": "novastack is a data framework to make AI easier to work with.",
                    }
                ],
                subscription_id="5d62977c-a53d-4b6d-bda1-7b79b3b9d1a0",
            )
            ```
        """
        data_sets = DataSets(wos_client=self._wos_client)

        return data_sets.store_feedback_records(
            request_records=request_records,
            subscription_id=subscription_id,
        )

    def create_custom_metric(
        self,
        name: str,
        metrics: list[WatsonxMetricSpec],
        integrated_system_url: str,
        integrated_system_credentials: IntegratedSystemCredentials,
        schedule: bool = False,
    ) -> dict:
        """
        Creates a custom metric definition for IBM watsonx.governance.

        This must be done before using custom metrics.

        Args:
            name (str): The name of the custom metric group.
            metrics (list[WatsonxMetricSpec]): A list of metrics to be measured.
            integrated_system_url (str): The URL of the external metric provider.
            integrated_system_credentials (IntegratedSystemCredentials): The credentials for the integrated system.
            schedule (bool, optional): Enable or disable the scheduler. Defaults to `False`.

        Example:
            ```python
            from novastack.observability.watsonx import (
                WatsonxMetricSpec,
                IntegratedSystemCredentials,
                WatsonxMetricThreshold,
            )

            client.create_custom_metric(
                name="Custom LLM Quality",
                metrics=[
                    WatsonxMetricSpec(
                        name="context_quality",
                        applies_to=[
                            "retrieval_augmented_generation",
                            "summarization",
                        ],
                        thresholds=[
                            WatsonxMetricThreshold(
                                threshold_type="lower_limit", default_value=0.75
                            )
                        ],
                    )
                ],
                integrated_system_url="IS_URL",
                integrated_system_credentials=IntegratedSystemCredentials(
                    auth_type="basic", username="USERNAME", password="PASSWORD"
                ),
            )
            ```
        """
        custom_metrics = CustomMetrics(wos_client=self._wos_client)

        return custom_metrics.create_metric_definition(
            name=name,
            metrics=metrics,
            integrated_system_url=integrated_system_url,
            integrated_system_credentials=integrated_system_credentials,
            schedule=schedule,
        )

    @deprecated(reason="Use `create_custom_metric` instead.", version="0.1.4")
    def create_custom_metric_definition(
        self,
        name: str,
        metrics: list[WatsonxMetricSpec],
        integrated_system_url: str,
        integrated_system_credentials: IntegratedSystemCredentials,
        schedule: bool = False,
    ) -> dict:
        return self.create_custom_metric(
            name=name,
            metrics=metrics,
            integrated_system_url=integrated_system_url,
            integrated_system_credentials=integrated_system_credentials,
            schedule=schedule,
        )

    def associate_monitor_instance(
        self,
        integrated_system_id: str,
        monitor_definition_id: str,
        subscription_id: str,
    ):
        """
        Associate the specified monitor definition to the specified subscription.

        Args:
            integrated_system_id (str): The ID of the integrated system.
            monitor_definition_id (str): The ID of the custom metric monitor instance.
            subscription_id (str): The ID of the subscription to associate the monitor with.

        Example:
            ```python
            client.associate_monitor_instance(
                integrated_system_id="019667ca-5687-7838-8d29-4ff70c2b36b0",
                monitor_definition_id="custom_llm_quality",
                subscription_id="0195e95d-03a4-7000-b954-b607db10fe9e",
            )
            ```
        """
        custom_metrics = CustomMetrics(wos_client=self._wos_client)

        return custom_metrics.associate_monitor_instance(
            integrated_system_id=integrated_system_id,
            monitor_definition_id=monitor_definition_id,
            subscription_id=subscription_id,
        )

    def log_measurements(
        self,
        monitor_instance_id: str,
        run_id: str,
        request_records: dict[str, float | int],
    ):
        """
        Log aggregated metrics measurements to the specified custom monitor instance.

        Args:
            monitor_instance_id (str): The unique ID of the monitor instance.
            run_id (str): The ID of the monitor run that generated the metrics.
            request_records (dict[str | float | int]): dict containing the metrics to be published.

        Example:
            ```python
            client.log_measurements(
                monitor_instance_id="01966801-f9ee-7248-a706-41de00a8a998",
                run_id="RUN_ID",
                request_records={"context_quality": 0.914, "sensitivity": 0.85},
            )
            ```
        """
        custom_metrics = CustomMetrics(wos_client=self._wos_client)

        return custom_metrics.log_measurements(
            monitor_instance_id=monitor_instance_id,
            run_id=run_id,
            request_records=request_records,
        )

    @deprecated(reason="Use `log_measurements` instead.", version="0.1.4")
    def log_metrics(
        self,
        monitor_instance_id: str,
        run_id: str,
        request_records: dict[str, float | int],
    ):
        return self.log_measurements(
            monitor_instance_id=monitor_instance_id,
            run_id=run_id,
            request_records=request_records,
        )

    def log_record_measurements(
        self,
        custom_data_set_id: str,
        reference_data_set_id: str,
        computed_on: str,
        run_id: str,
        request_records: list[dict],
    ):
        """
        Log record-level measurements for individual records in the custom dataset.

        Args:
            custom_data_set_id (str): The ID of the custom metric data set.
            reference_data_set_id (str): The dataset ID on which the metric was calculated.
            computed_on (str): The dataset on which the metric was calculated (e.g., payload or feedback).
            run_id (str): The ID of the monitor run that generated the metrics.
            request_records (list[dict]): A list of dictionaries containing the records to be stored.

        Example:
            ```python
            client.log_record_measurements(
                custom_data_set_id="CUSTOM_DATASET_ID",
                reference_data_set_id="COMPUTED_ON_DATASET_ID",
                computed_on="payload",
                run_id="RUN_ID",
                request_records=[
                    {
                        "reference_record_id": "COMPUTED_ON_RECORD_ID",
                        "record_timestamp": "2025-12-09T00:00:00Z",
                        "context_quality": 0.786,
                        "pii": 0.05,
                    }
                ],
            )
            ```
        """
        custom_metrics = CustomMetrics(wos_client=self._wos_client)

        return custom_metrics.log_record_measurements(
            custom_data_set_id=custom_data_set_id,
            reference_data_set_id=reference_data_set_id,
            computed_on=computed_on,
            run_id=run_id,
            request_records=request_records,
        )

    @deprecated(reason="Use `log_record_measurements` instead.", version="0.1.4")
    def log_record_metrics(
        self,
        custom_data_set_id: str,
        reference_data_set_id: str,
        computed_on: str,
        run_id: str,
        request_records: list[dict],
    ):
        return self.log_record_measurements(
            custom_data_set_id=custom_data_set_id,
            reference_data_set_id=reference_data_set_id,
            computed_on=computed_on,
            run_id=run_id,
            request_records=request_records,
        )
