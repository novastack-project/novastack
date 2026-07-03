import datetime
import uuid
from typing import Any

from novastack.core.bridge.pydantic import BaseModel
from novastack.core.utils import validate_enum
from novastack.observability.watsonx.enums import DataSetType
from novastack.observability.watsonx.integrated_system import (
    IntegratedSystemCredentials,
)
from novastack.observability.watsonx.schemas import WatsonxMetricSpec
from novastack.observability.watsonx.supporting_classes.utils import suppress_output


class CustomMetrics(BaseModel):
    """
    Internal helper class for managing custom metrics operations.

    Provides methods to create metric definitions, associate monitor instances,
    and log custom metric measurements.
    Wraps the WOS client to simplify custom metrics management.
    """

    wos_client: Any

    def _get_patch_request_field(
        self,
        field_path: str,
        field_value: Any,
        op_name: str = "replace",
    ) -> dict:
        return {"op": op_name, "path": field_path, "value": field_value}

    def _add_integrated_system(
        self,
        credentials: IntegratedSystemCredentials,
        name: str,
        endpoint: str,
    ) -> str:
        custom_metrics_integrated_system = self.wos_client.integrated_systems.add(
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
        _monitor_runtime = MonitorRuntime(type="custom_metrics_provider")

        if schedule:
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
        else:
            # Known issue with watsonx schedule. Long repeat interval as workaround.
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

        custom_monitor_details = self.wos_client.monitor_definitions.add(
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
        monitor_instances = self.wos_client.monitor_instances.list(
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
        payload = self._get_patch_request_field(
            "/parameters",
            {
                "custom_metrics_provider_id": integrated_system_id,
                "custom_metrics_wait_time": 60,
                "enable_custom_metric_runs": True,
            },
        )

        return self.wos_client.monitor_instances.update(
            custom_monitor_id,
            [payload],
            update_metadata_only=True,
        ).result

    def create_metric_definition(
        self,
        name: str,
        metrics: list[WatsonxMetricSpec],
        integrated_system_url: str,
        integrated_system_credentials: IntegratedSystemCredentials,
        schedule: bool = False,
    ) -> dict[str, Any]:
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
        payload = self._get_patch_request_field(
            "/parameters",
            {"monitor_definition_ids": [external_monitor_id]},
            op_name="add",
        )

        self.wos_client.integrated_systems.update(integrated_system_id, [payload])

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
        from ibm_watson_openscale.base_classes.watson_open_scale_v2 import Target

        data_marts = self.wos_client.data_marts.list().result.data_marts
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
                self.wos_client.monitor_instances.create,
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

        self.wos_client.custom_monitor.create_custom_dataset(
            data_mart_id=data_mart_id,
            subscription_id=subscription_id,
            custom_monitor_id=monitor_definition_id,
        )

        return monitor_instance_details

    def log_metrics(
        self,
        monitor_instance_id: str,
        run_id: str,
        request_records: dict[str, float | int],
    ):
        from ibm_watson_openscale.base_classes.watson_open_scale_v2 import (
            MonitorMeasurementRequest,
            Runs,
        )

        measurement_request = MonitorMeasurementRequest(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            run_id=run_id,
            metrics=[request_records],
        )

        self.wos_client.monitor_instances.add_measurements(
            monitor_instance_id=monitor_instance_id,
            monitor_measurement_request=[measurement_request],
        ).result

        run = Runs(watson_open_scale=self.wos_client)
        patch_payload = [
            self._get_patch_request_field("/status/state", "finished"),
            self._get_patch_request_field(
                "/status/completed_at",
                datetime.datetime.now(datetime.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                ),
            ),
        ]

        return run.update(
            monitor_instance_id=monitor_instance_id,
            monitoring_run_id=run_id,
            json_patch_operation=patch_payload,
        ).result

    def log_record_metrics(
        self,
        custom_data_set_id: str,
        reference_data_set_id: str,
        computed_on: str,
        run_id: str,
        request_records: list[dict],
    ):
        validate_enum(computed_on, "computed_on", DataSetType)

        if request_records:
            for record in request_records:
                record["record_id"] = str(uuid.uuid4())
                record["run_id"] = run_id
                record["computed_on"] = computed_on
                record["data_set_id"] = reference_data_set_id

            fields = list(dict.fromkeys(k for d in request_records for k in d))

            return self.wos_client.data_sets.store_records(
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
