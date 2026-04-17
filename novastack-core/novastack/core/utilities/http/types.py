from typing import Any

from novastack.core.bridge.pydantic import BaseModel, Field


class HttpRetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_retries: int = Field(
        default=3, ge=0, description="Maximum number of retry attempts"
    )
    retry_delay: float = Field(
        default=1.0, gt=0, description="Delay between retries in seconds"
    )


class HttpResponse(BaseModel):
    """HTTP Response wrapper."""

    model_config = {"arbitrary_types_allowed": True}

    status_code: int = Field(..., description="HTTP status code")
    headers: dict[str, str] = Field(
        default_factory=dict, description="HTTP Response Headers"
    )
    content: bytes = Field(default=b"", description="Raw Response Content")
    url: str = Field(...)

    def json_dump(self) -> Any:
        """
        Parse response content as JSON.

        Returns:
            Parsed JSON content

        Raises:
            ValueError: If content is not valid JSON
        """
        import json

        try:
            return json.loads(self.content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to parse response as JSON: {e}")
