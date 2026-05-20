
def validate_enum(el: str, el_name: str, expected_enum) -> str:
    allowed = {
        getattr(expected_enum, attr)
        for attr in vars(expected_enum)
        if attr.isupper()
    }

    if el not in allowed:
        raise ValueError("Invalid {} '{}'. Input should be: {}.".format(
                    el_name, el, sorted(allowed)
                ))

    return el
