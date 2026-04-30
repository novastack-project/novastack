import datetime
import uuid
from typing import Any, Literal

from novastack.core.bridge.pydantic import BaseModel, PrivateAttr, SecretStr
from novastack.observability.watsonx.supporting_classes.clients import (
    WosClientFactory,
)
from novastack.observability.watsonx.supporting_classes.credentials import (
    CloudPakforDataCredentials,
    IntegratedSystemCredentials,
)
from novastack.observability.watsonx.supporting_classes.enums import DataSetType, Region
from novastack.observability.watsonx.supporting_classes.metric import (
    WatsonxMetricSpec,
)
from novastack.observability.watsonx.utils.instrumentation import suppress_output


class WatsonxCustomMetricsManager(BaseModel):
    """
    Provides functionality to set up a custom metric to measure your model's performance with IBM watsonx.governance.

    Attributes:
        api_key (str): The API key for IBM watsonx.governance.
        region (Region, optional): The region where watsonx.governance is hosted when using IBM Cloud.
            Defaults to `us-south`.
        cpd_creds (CloudPakforDataCredentials, optional): IBM Cloud Pak for Data environment credentials.
        service_instance_id (str, optional): The service instance ID.

    Example:
        ```python
        from novastack.observability.watsonx.supporting_classes.enums import Region

        from novastack.observability.watsonx import (
            WatsonxCustomMetricsManager,
            CloudPakforDataCredentials,
        )

        # watsonx.governance (IBM Cloud)
        wxgov_client = WatsonxCustomMetricsManager(
            api_key="API_KEY", region=Region.US_SOUTH
        )

        # watsonx.governance (CP4D)
        cpd_creds = CloudPakforDataCredentials(
            url="CPD_URL",
            username="USERNAME",
            password="PASSWORD",
            version="5.2",
            instance_id="openshift",
        )

        wxgov_client = WatsonxCustomMetricsManager(cpd_creds=cpd_creds)
        ```
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    api_key: SecretStr | None = None
    region: Region = Region.US_SOUTH
    cpd_creds: CloudPakforDataCredentials | None = None
    service_instance_id: str | None = None

    _wos_client: Any | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:  # noqa: PYI063
        self.region = Region.enum_validate(self.region)

        if not self._wos_client:
            self._wos_client = WosClientFactory.create_client(
                api_key=self.api_key,
                region=self.region,
                cpd_creds=self.cpd_creds,
                service_instance_id=self.service_instance_id,
            )

    def _add_integrated_system(
        self,
        credentials: IntegratedSystemCredentials,
        name: str,
        endpoint: str,
    ) -> str:
        custom_metrics_integrated_system = self._wos_client.integrated_systems.add(
            name=name,
            description="Integrated system created by novastack.",
            type="custom_metrics_provider",
            credentials=credentials.to_dict(),
            connection={"display_name": name, "endpoint": endpoint},
        ).result

        return custom_metrics_integrated_system.metadata.id

    def _add_monitor_definitions(
        self,
        name: str,
        metrics: list[WatsonxMetricSpec],
        schedule: bool,
    ) -> str:
        from ibm_watson_openscale.base_classes.watson_open_scale_v2 import (
            ApplicabilitySelection,
            MonitorInstanceSchedule,
            MonitorMetricRequest,
            MonitorRuntime,
            ScheduleStartTime,
        )

        _metrics = [MonitorMetricRequest(**metric.to_dict()) for metric in metrics]
        _monitor_runtime = None
        _monitor_schedule = None

        if schedule:
            _monitor_runtime = MonitorRuntime(type="custom_metrics_provider")
            _monitor_schedule = MonitorInstanceSchedule(
                repeat_interval=1,
                repeat_type="hour",
                repeat_unit="hour",
                status="enabled",
                start_time=ScheduleStartTime(
                    type="relative",
                    delay_unit="minute",
                    delay=30,
                ),
            )
        else:  # Known issue with watsonx schedule. Long repeat interval as workaround.
            _monitor_runtime = MonitorRuntime(type="custom_metrics_provider")
            _monitor_schedule = MonitorInstanceSchedule(
                repeat_interval=10,
                repeat_type="year",
                repeat_unit="year",
                status="enabled",
                start_time=ScheduleStartTime(
                    type="relative",
                    delay_unit="minute",
                    delay=30,
                ),
            )

        custom_monitor_details = self._wos_client.monitor_definitions.add(
            name=name,
            metrics=_metrics,
            tags=[],
            schedule=_monitor_schedule,
            applies_to=ApplicabilitySelection(input_data_type=["unstructured_text"]),
            monitor_runtime=_monitor_runtime,
            background_mode=False,
        ).result

        return custom_monitor_details.metadata.id

    def _get_monitor_instance(self, subscription_id: str, monitor_definition_id: str):
        monitor_instances = self._wos_client.monitor_instances.list(
            monitor_definition_id=monitor_definition_id,
            target_target_id=subscription_id,
        ).result.monitor_instances

        if len(monitor_instances) == 1:
            return monitor_instances[0]
        else:
            return None

    def _update_monitor_instance(
        self,
        integrated_system_id: str,
        custom_monitor_id: str,
    ):
        payload = [
            {
                "op": "replace",
                "path": "/parameters",
                "value": {
                    "custom_metrics_provider_id": integrated_system_id,
                    "custom_metrics_wait_time": 60,
                    "enable_custom_metric_runs": True,
                },
            },
        ]

        return self._wos_client.monitor_instances.update(
            custom_monitor_id,
            payload,
            update_metadata_only=True,
        ).result

    def _get_patch_request_field(
        self,
        field_path: str,
        field_value: Any,
        op_name: str = "replace",
    ) -> dict:
        return {"op": op_name, "path": field_path, "value": field_value}

    def _get_dataset_id(
        self,
        subscription_id: str,
        data_set_type: Literal["feedback", "payload_logging"],
    ) -> str:
        data_sets = self._wos_client.data_sets.list(
            target_target_id=subscription_id,
            type=data_set_type,
        ).result.data_sets
        data_set_id = None
        if len(data_sets) > 0:
            data_set_id = data_sets[0].metadata.id
        return data_set_id

    def _get_dataset_data(self, data_set_id: str):
        json_data = self._wos_client.data_sets.get_list_of_records(
            data_set_id=data_set_id,
            format="list",
        ).result

        if not json_data.get("records"):
            return None

        return json_data["records"][0]

    def _get_existing_data_mart(self):
        data_marts = self._wos_client.data_marts.list().result.data_marts
        if len(data_marts) == 0:
            raise Exception(
                "No data marts found. Please ensure at least one data mart is available.",
            )

        return data_marts[0].metadata.id

    def create_metric_definition(
        self,
        name: str,
        metrics: list[WatsonxMetricSpec],
        integrated_system_url: str,
        integrated_system_credentials: IntegratedSystemCredentials,
        schedule: bool = False,
    ) -> dict[str, Any]:
        """
        Creates a custom metric definition for IBM watsonx.governance.

        This must be done before using custom metrics.

        Args:
            name (str): The name of the custom metric group.
            metrics (list[WatsonxMetricSpec]): A list of metrics to be measured.
            schedule (bool, optional): Enable or disable the scheduler. Defaults to `False`.
            integrated_system_url (str): The URL of the external metric provider.
            integrated_system_credentials (IntegratedSystemCredentials): The credentials for the integrated system.

        Example:
            ```python
            from novastack.observability.watsonx import (
                WatsonxMetricSpec,
                IntegratedSystemCredentials,
                WatsonxMetricThreshold,
            )

            wxgov_client.create_metric_definition(
                name="Custom Metric - Custom LLM Quality",
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
                integrated_system_url="IS_URL",  # URL to the endpoint computing the metric
                integrated_system_credentials=IntegratedSystemCredentials(
                    auth_type="basic", username="USERNAME", password="PASSWORD"
                ),
            )
            ```
        """
        if len(name) > 27:
            raise ValueError(
                f"Invalid parameter 'name': length must be less than or equal to 27 (received {len(name)})."
            )

        integrated_system_id = self._add_integrated_system(
            integrated_system_credentials,
            name,
            integrated_system_url,
        )

        external_monitor_id = suppress_output(
            self._add_monitor_definitions,
            name,
            metrics,
            schedule,
        )

        # Associate the external monitor with the integrated system
        payload = [
            {
                "op": "add",
                "path": "/parameters",
                "value": {"monitor_definition_ids": [external_monitor_id]},
            },
        ]

        self._wos_client.integrated_systems.update(integrated_system_id, payload)

        return {
            "integrated_system_id": integrated_system_id,
            "monitor_definition_id": external_monitor_id,
        }

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
            wxgov_client.associate_monitor_instance(
                integrated_system_id="019667ca-5687-7838-8d29-4ff70c2b36b0",
                monitor_definition_id="custom_llm_quality",
                subscription_id="0195e95d-03a4-7000-b954-b607db10fe9e",
            )
            ```
        """
        from ibm_watson_openscale.base_classes.watson_open_scale_v2 import Target

        data_marts = self._wos_client.data_marts.list().result.data_marts
        if len(data_marts) == 0:
            raise Exception(
                "No data marts found. Please ensure at least one data mart is available.",
            )

        data_mart_id = data_marts[0].metadata.id
        existing_monitor_instance = self._get_monitor_instance(
            subscription_id,
            monitor_definition_id,
        )

        if existing_monitor_instance is None:
            target = Target(target_type="subscription", target_id=subscription_id)

            parameters = {
                "custom_metrics_provider_id": integrated_system_id,
                "custom_metrics_wait_time": 60,
                "enable_custom_metric_runs": True,
            }

            monitor_instance_details = suppress_output(
                self._wos_client.monitor_instances.create,
                data_mart_id=data_mart_id,
                background_mode=False,
                monitor_definition_id=monitor_definition_id,
                target=target,
                parameters=parameters,
            ).result
        else:
            existing_instance_id = existing_monitor_instance.metadata.id
            monitor_instance_details = self._update_monitor_instance(
                integrated_system_id,
                existing_instance_id,
            )

        self._wos_client.custom_monitor.create_custom_dataset(
            data_mart_id=data_mart_id,
            subscription_id=subscription_id,
            custom_monitor_id=monitor_definition_id,
        )

        return monitor_instance_details

    def store_metric_data(
        self,
        monitor_instance_id: str,
        run_id: str,
        request_records: dict[str, float | int],
    ):
        """
        Stores computed metrics data to the specified monitor instance.

        Args:
            monitor_instance_id (str): The unique ID of the monitor instance.
            run_id (str): The ID of the monitor run that generated the metrics.
            request_records (dict[str | float | int]): dict containing the metrics to be published.

        Example:
            ```python
            wxgov_client.store_metric_data(
                monitor_instance_id="01966801-f9ee-7248-a706-41de00a8a998",
                run_id="RUN_ID",
                request_records={"context_quality": 0.914, "sensitivity": 0.85},
            )
            ```
        """
        from ibm_watson_openscale.base_classes.watson_open_scale_v2 import (
            MonitorMeasurementRequest,
            Runs,
        )

        measurement_request = MonitorMeasurementRequest(
            timestamp=datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ),
            run_id=run_id,
            metrics=[request_records],
        )

        self._wos_client.monitor_instances.add_measurements(
            monitor_instance_id=monitor_instance_id,
            monitor_measurement_request=[measurement_request],
        ).result

        run = Runs(watson_open_scale=self._wos_client)
        patch_payload = []
        patch_payload.append(self._get_patch_request_field("/status/state", "finished"))
        patch_payload.append(
            self._get_patch_request_field(
                "/status/completed_at",
                datetime.datetime.now(datetime.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                ),
            ),
        )

        return run.update(
            monitor_instance_id=monitor_instance_id,
            monitoring_run_id=run_id,
            json_patch_operation=patch_payload,
        ).result

    def store_record_metric_data(
        self,
        custom_data_set_id: str,
        reference_data_set_id: str,
        computed_on: DataSetType,
        run_id: str,
        request_records: list[dict],
    ):
        """
        Stores computed metrics data to the specified transaction record.

        Args:
            custom_data_set_id (str): The ID of the custom metric data set.
            reference_data_set_id (str): The dataset ID on which the metric was calculated.
            computed_on (DataSetType): The dataset on which the metric was calculated (e.g., payload or feedback).
            run_id (str): The ID of the monitor run that generated the metrics.
            request_records (list[dict]): A list of dictionaries containing the records to be stored.

        Example:
            ```python
            wxgov_client.store_record_metric_data(
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
        computed_on = DataSetType.enum_validate(computed_on).value

        if request_records:
            for record in request_records:
                record["record_id"] = str(uuid.uuid4())
                record["run_id"] = run_id
                record["computed_on"] = computed_on
                record["data_set_id"] = reference_data_set_id

            fields = list(dict.fromkeys(k for d in request_records for k in d))

            return self._wos_client.data_sets.store_records(
                data_set_id=custom_data_set_id,
                request_body=[
                    {
                        "fields": fields,
                        "values": [
                            [row.get(f) for f in fields] for row in request_records
                        ],
                    }
                ],
            ).result

        return None
