import json
from typing import Any, Literal

from ibm_watson_openscale.supporting_classes.enums import (
    DataSetTypes,
    TargetTypes,
)
from novastack.core.bridge.pydantic import BaseModel
from novastack.observability.watsonx.supporting_classes.utils import (
    build_payload,
    suppress_output,
    validate_and_filter_dict,
)


class DataSets(BaseModel):
    """
    Internal helper class for managing data sets operations.

    Provides methods to store records for payload and feedback logging.
    Wraps the WOS client to simplify logging of LLM interactions,
    handling subscription management, data set retrieval, and record formatting.
    """

    wos_client: Any

    def get_id(
        self,
        subscription_id: str,
        data_set_type: Literal["feedback", "payload_logging"],
    ) -> str | None:
        """
        Retrieves the ID of the data set matching the subscription and type.

        Args:
            subscription_id (str): The ID of the subscription associated with the data set.
            data_set_type (Literal["feedback", "payload_logging"]): The type of data set to retrieve.
        """
        data_sets = self.wos_client.data_sets.list(
            target_target_id=subscription_id,
            type=data_set_type,
        ).result.data_sets

        data_set_id = None
        if len(data_sets) > 0:
            data_set_id = data_sets[0].metadata.id

        return data_set_id

    def get_records(
        self,
        data_set_id: str,
    ) -> str | None:
        """
        Retrieves the records by the specified data set.

        Args:
            data_set_id (str): The ID of the data set to query.
        """
        json_data = self.wos_client.data_sets.get_list_of_records(
            data_set_id=data_set_id,
            format="list",
        ).result

        if not json_data.get("records"):
            return None

        return json_data["records"][0]

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
        if subscription_id is None or subscription_id == "":
            raise ValueError(
                "Unexpected value for 'subscription_id': Cannot be None or empty string."
            )

        subscription_details = self.wos_client.subscriptions.get(
            subscription_id,
        ).result
        subscription_details = json.loads(str(subscription_details))

        feature_fields = subscription_details["entity"]["asset_properties"][
            "feature_fields"
        ]

        payload_data_set_id = (
            self.wos_client.data_sets.list(
                type=DataSetTypes.PAYLOAD_LOGGING,
                target_target_id=subscription_id,
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
        if subscription_id is None or subscription_id == "":
            raise ValueError(
                "Unexpected value for 'subscription_id': Cannot be None or empty string."
            )

        subscription_details = self.wos_client.subscriptions.get(
            subscription_id,
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
                target_target_id=subscription_id,
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
