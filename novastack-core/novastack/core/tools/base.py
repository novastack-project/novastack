import re
from abc import ABC, abstractmethod
from typing import Any, Literal

from novastack.core.bridge.pydantic import BaseModel, Field, field_validator


class ToolInputSchema(BaseModel):
    """
    Schema for defining tool input parameters.

    Attributes:
        description: Description of the input parameter.
        input_type: Type of the input parameter (integer or string).
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    description: str = Field(
        ...,
        description="Description of the input parameter",
        min_length=1,
    )
    input_type: Literal["integer", "string"] = Field(
        ...,
        description="Type of the input parameter",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the schema to a dictionary."""
        return self.model_dump()


class BaseTool(BaseModel, ABC):
    """
    Abstract base class defining the interface for tools.

    Attributes:
        name: Tool name (only letters, digits, and underscores allowed).
        description: Description of the tool's functionality.
        input_schema: Input schema for the tool.
    """

    model_config = {"arbitrary_types_allowed": True}

    name: str = Field(
        ...,
        description="Tool name",
        min_length=1,
        pattern=r"^[A-Za-z0-9_]+$",
    )
    description: str = Field(
        ...,
        description="Tool description",
        min_length=1,
    )
    input_schema: dict[str, ToolInputSchema] = Field(
        default_factory=dict,
        description="Input schema for the tool",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_]+$", v):
            raise ValueError(
                "Invalid name: only letters, digits, and underscores are allowed. "
                "No spaces or special characters.",
            )
        return v

    @classmethod
    def class_name(cls) -> str:
        return "BaseTool"

    @abstractmethod
    def run(self, tool_input: dict[str, Any]) -> Any:
        """
        Execute the tool with the provided parameters.

        Args:
            tool_input: Dictionary containing the input parameters.
        """
