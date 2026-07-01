from __future__ import annotations

import inspect
import threading
from datetime import datetime
from typing import Any

from ibm_cloud_sdk_core.authenticators import Authenticator as IBMAuthenticator
from novastack.core.bridge.pydantic import Field, PrivateAttr, field_validator
from novastack.core.instrumentation.events import BaseEvent
from novastack.core.instrumentation.events.llm import (
    LLMCompletionEndEvent,
    LLMCompletionStartEvent,
)
from novastack.core.instrumentation.span import Span
from novastack.core.observability import BaseObservability
from novastack.core.prompts import PromptTemplate
from novastack.core.prompts.utils import extract_template_vars
from novastack.observability.watsonx.enums import Region
from novastack.observability.watsonx.external_monitor_manager import (
    WatsonxExternalMonitorManager,
)


class WatsonxObservability(BaseObservability):
    """
    Add observability to Novastack LLM Calls with IBM watsonx.governance.

    Attributes:
        authenticator (IBMAuthenticator): The authenticator specifies the authentication mechanism.
        subscription_id (str, optional): The subscription ID associated with the records being logged.
        region (str, optional): The region where watsonx.governance is hosted when using IBM Cloud.
            Defaults to `us-south`.
        service_instance_id (str, optional): The service instance ID.

    Example:
        ```python
        from novastack.core import set_global_handler
        from novastack.observability.watsonx import WatsonxObservability

        # watsonx.governance (IBM Cloud)
        watsonx_handler = WatsonxObservability(
            authenticator=IAMAuthenticator(api_key="API_KEY"),
            subscription_id="SUBSCRIPTION_ID",
        )

        set_global_handler(watsonx_handler)
        ```
    """

    open_spans: dict[str, Span] = Field(
        default_factory=dict, description="Dictionary of open spans."
    )
    open_events: dict[str, BaseEvent] = Field(
        default_factory=dict, description="Dictionary of start events."
    )
    _lock: threading.Lock | None = PrivateAttr(default=None)

    authenticator: IBMAuthenticator
    subscription_id: str
    region: str = Region.US_SOUTH
    service_instance_id: str | None = None

    input_field_name: str = Field(
        default="input_text",
        description="Column name used to store input message content into a structured format. Defaults to 'input_text'.",
    )
    prompt_template: PromptTemplate | None = Field(
        default=None, description="Template for formatting prompts"
    )

    @field_validator("prompt_template", mode="before")
    @classmethod
    def _normalize_prompt_template(cls, value):
        if value is not None:
            return PromptTemplate.model_validate_input(value)
        return value

    @classmethod
    def class_name(cls) -> str:
        return "WatsonxObservability"

    @property
    def lock(self) -> threading.Lock:
        if self._lock is None:
            self._lock = threading.Lock()
        return self._lock

    def on_event(self, event: BaseEvent, **kwargs: Any) -> None:
        """Handle an event."""
        if isinstance(event, LLMCompletionStartEvent):
            with self.lock:
                self.open_events[event.span_id] = event

        if isinstance(event, LLMCompletionEndEvent):
            text = event.response.text
            input_token_count = event.response.input_token_count
            generated_token_count = event.response.generated_token_count
            span_id = event.span_id

            with self.lock:
                llm_start_event = self.open_events.pop(span_id, None)
                span = self.open_spans.pop(span_id, None)
                if span:
                    span.end_time = datetime.now()
                    span.duration = (span.end_time - span.start_time).total_seconds()

                    prompt_variables = (
                        extract_template_vars(
                            self.prompt_template.template,
                            llm_start_event.prompt or "",
                        )
                        if self.prompt_template
                        else {}
                    )

                    wxgov_client = WatsonxExternalMonitorManager(
                        authenticator=self.authenticator,
                        region=self.region,
                        service_instance_id=self.service_instance_id,
                    )

                    wxgov_client.log_payload_records(
                        subscription_id=self.subscription_id,
                        request_records=[
                            {
                                **prompt_variables,
                                "generated_text": text,
                                "input_token_count": input_token_count,
                                "generated_token_count": generated_token_count,
                                "response_time": span.duration,
                            }
                        ],
                    )

    def on_span_start(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span start."""
        span = Span(id_=id_, parent_id=parent_id, metadata=metadata or {})
        with self.lock:
            self.open_spans[id_] = span
