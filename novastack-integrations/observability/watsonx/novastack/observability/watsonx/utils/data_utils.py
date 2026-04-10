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
