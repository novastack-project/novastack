def validate_enum(el: str, el_name: str, expected_enum) -> str:
    allowed = {
        getattr(expected_enum, attr) for attr in vars(expected_enum) if attr.isupper()
    }

    if el not in allowed:
        raise ValueError(
            "Invalid {} '{}'. Input should be: {}.".format(el_name, el, sorted(allowed))
        )

    return el


def validate_type(el, el_name: str, expected_type: type | list[type]):
    if type(expected_type) is not type and type(expected_type) is not list:
        raise TypeError(
            "Invalid expected_type type '{}'. Input should be: ['type', 'list[type]'].".format(
                expected_type
            )
        )

    if type(expected_type) is list:
        if not any(isinstance(el, t) for t in expected_type):
            allowed = ", ".join(t.__name__ for t in expected_type)
            raise TypeError(
                "Invalid {} type '{}'. Input should be: [{}].".format(
                    el_name, type(el).__name__, allowed
                )
            )
        return el
    else:
        if not isinstance(el, expected_type):  # type: ignore
            raise TypeError(
                "Invalid {} type '{}'. Input should be: '{}'.".format(
                    el_name, type(el).__name__, expected_type.__name__
                )
            )

    return el
