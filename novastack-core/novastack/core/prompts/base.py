from __future__ import annotations

import re
from typing import Any

from novastack.core.bridge.pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from novastack.core.prompts.utils import SafeFormatter


class PromptTemplate(BaseModel):
    """
    Prompt Template with variable placeholders.

    Attributes:
        template (str): Prompt template string with placeholders in {variable} format.

    Example:
        ```python
        from novastack.core.prompts import PromptTemplate

        # Create template
        prompt = PromptTemplate(template="Summarize the following text: {input_text}")

        # Format with variables
        formatted = prompt.format(input_text="Hello World")

        # Get template variables
        variables = prompt.get_template_variables()
        ```
    """

    model_config = ConfigDict(
        validate_assignment=True,
    )

    template: str = Field(
        description="Prompt template string with placeholders in {variable} format",
    )

    def __init__(self, template: str):
        super().__init__(template=template)

    @classmethod
    def from_value(cls, value: str | PromptTemplate | None) -> PromptTemplate | None:
        """Creates a PromptTemplate from different input types."""
        if value is None:
            return None

        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            return cls(template=value)

        raise TypeError(
            f"Invalid type for parameter 'template'. Expected str or PromptTemplate, but received {type(value).__name__}."
        )

    def _map_template_vars(self) -> list[str]:
        """
        Extracts all variables from the template.

        Example:
            ```python
            prompt = PromptTemplate(template="Hello {name}, you are {age} years old")
            variables = prompt.get_template_variables()
            # ['name', 'age']
            ```
        """
        pattern = re.compile(r"\{([^{}]+)\}")
        return pattern.findall(self.template)

    def format(self, **kwargs: Any) -> str:
        """
        Formats the template using the provided variables.
        Missing variables are left as placeholders.

        Args:
            **kwargs: Variables to substitute in the template

        Example:
            ```python
            prompt = PromptTemplate(template="Hello {name}, you are {age} years old")
            result = prompt.format(name="Alice")
            # "Hello Alice, you are {age} years old"
            ```
        """
        return self.template.format_map(SafeFormatter(**kwargs))

    def __str__(self) -> str:
        return self.template
