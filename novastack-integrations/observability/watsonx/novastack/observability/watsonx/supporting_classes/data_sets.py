import json
from typing import TYPE_CHECKING

from novastack.core.bridge.pydantic import BaseModel, PrivateAttr
from novastack.observability.watsonx.supporting_classes.utils import (
    build_payload,
    suppress_output,
    validate_and_filter_dict,
)

if TYPE_CHECKING:
    from novastack.observability.watsonx.supporting_classes.clients import (
        WosClientFactory,
    )


class DataSets(BaseModel):
    """
    Internal helper class for managing data sets operations.

    Provides methods to store records for payload and feedback logging.
    Wraps the WOS client to simplify logging of LLM interactions,
    handling subscription management, data set retrieval, and record formatting.
    """

    wos_client: WosClientFactory = PrivateAttr()

    def store_payload_records(
        self,
        request_records: list[dict],
        subscription_id: str | None = None,
    ) -> list[str]:
        """
        Stores records to the payload logging system.

        Args:
            request_records (list[dict]): A list of records to be logged. Each record is represented as a dictionary.
            subscription_id (str, optional): The subscription ID associated with the records being logged.
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

        subscription_details = self.wos_client.subscriptions.get(
            _subscription_id,
        ).result
        subscription_details = json.loads(str(subscription_details))

        feature_fields = subscription_details["entity"]["asset_properties"][
            "feature_fields"
        ]

        payload_data_set_id = (
            self.wos_client.data_sets.list(
                type=DataSetTypes.PAYLOAD_LOGGING,
                target_target_id=_subscription_id,
                target_target_type=TargetTypes.SUBSCRIPTION,
            )
            .result.data_sets[0]
            .metadata.id
        )

        payload_data = build_payload(request_records, feature_fields)

        suppress_output(
            self.wos_client.data_sets.store_records,
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

        Args:
            request_records (list[dict]): A list of records to be logged, where each record is represented as a dictionary.
            subscription_id (str, optional): The subscription ID associated with the records being logged.
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

        subscription_details = self.wos_client.subscriptions.get(
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
            self.wos_client.data_sets.list(
                type=DataSetTypes.FEEDBACK,
                target_target_id=_subscription_id,
                target_target_type=TargetTypes.SUBSCRIPTION,
            )
            .result.data_sets[0]
            .metadata.id
        )

        suppress_output(
            self.wos_client.data_sets.store_records,
            data_set_id=feedback_data_set_id,
            request_body=request_records,
            background_mode=False,
        )

        return {"status": "success"}
