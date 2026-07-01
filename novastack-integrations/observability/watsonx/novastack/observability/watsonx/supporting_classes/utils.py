import contextlib
import io
import uuid
from collections.abc import Callable
from typing import Any


def build_payload(
    records: list[dict],
    feature_fields: list[str],
) -> list[dict[str, Any]]:
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


def suppress_output(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """
    Runs the given function while suppressing all print output (stdout).

    Args:
        fn: The function to run silently.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        The return value of the function.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def validate_and_filter_dict(
    original_dict: dict, optional_keys: list, required_keys: list | None = None
):
    """
    Validates that all required keys are present in a dictionary and returns a filtered dictionary
    containing only the required and specified optional keys with non-None values.

    Args:
        original_dict (dict): The original dictionary.
        optional_keys (list): A list of keys to retain.
        required_keys (list, optional): A list of keys that must be present in the dictionary. Defaults to None.
    """
    # Ensure all required keys are in the source dict
    if required_keys is None:
        required_keys = []

    missing_keys = [key for key in required_keys if key not in original_dict]
    if missing_keys:
        raise KeyError(
            f"Validation failed: the following required key(s) are missing from the dictionary: {missing_keys}. "
            "Please provide these keys before proceeding."
        )

    all_keys_to_keep = set(required_keys + optional_keys)

    # Create a new dictionary with only the key-value pairs where the key is in 'keys' and value is not None
    return {
        key: original_dict[key]
        for key in all_keys_to_keep
        if key in original_dict and original_dict[key] is not None
    }


def validate_container_id(
    project_id: str | None,
    space_id: str | None,
) -> None:
    """
    Validates container_id parameter `project_id` or `space_id` is provided.

    Args:
        project_id (str | None): The project ID.
        space_id (str | None): The space ID.
    """
    if (not (project_id or space_id)) or (project_id and space_id):
        raise ValueError(
            "Invalid configuration: Neither was provided: please set either 'project_id' or 'space_id'. "
            "Both were provided: 'project_id' and 'space_id' cannot be set at the same time."
        )


class retry_if_exception_wos_entitlement:
    def __init__(
        self,
        wos_client: Any,
        space_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        self._wos_client = wos_client
        self.space_id = space_id
        self.project_id = project_id

    def __call__(self, exception: Exception) -> bool:
        if not (
            getattr(exception, "status_code", None) == 403
            and "The user entitlement does not exist"
            in getattr(exception, "message", "")
        ):
            return False

        data_marts = self._wos_client.data_marts.list().result
        if (data_marts.data_marts is None) or (not data_marts.data_marts):
            return False

        data_mart_id = data_marts.data_marts[0].metadata.id

        self._wos_client.wos.add_instance_mapping(
            service_instance_id=data_mart_id,
            space_id=self.space_id,
            project_id=self.project_id,
        )
        return True
