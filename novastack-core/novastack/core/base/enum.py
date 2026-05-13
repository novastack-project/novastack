from enum import Enum
from typing import Any, Type, TypeVar

T = TypeVar("T", bound="BaseStrEnum")


class BaseStrEnum(str, Enum):
    @classmethod
    def from_value(cls: Type[T], value: Any) -> T:
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            normalized = value.lower()
            try:
                return cls(normalized)
            except ValueError:
                valid = [item.value for item in cls]
                raise ValueError(
                    f"Invalid value for {cls.__name__}. "
                    f"Received: '{value}'. Valid values are: {valid}."
                )

        raise TypeError(
            f"Invalid type for {cls.__name__}. "
            f"Expected str or {cls.__name__}, but received {type(value).__name__}."
        )
