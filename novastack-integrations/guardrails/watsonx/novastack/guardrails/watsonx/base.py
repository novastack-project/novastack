from typing import Any

import requests
from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.guardrails import BaseGuardrail, GuardrailResponse
from novastack.core.prompts import PromptTemplate
from novastack.guardrails.watsonx.supporting_classes.enums import Direction, Region


class WatsonxGuardrail(BaseGuardrail):
    """
    Provides functionality to interact with IBM watsonx.governance Guardrails.

    Info:
        Beekeeper currently does not support **agent_function_call_validation** policy provided by IBM Watsonx Governance Guardrails manager.

    Attributes:
        api_key (str): The API key for IBM watsonx.governance.
        policy_id (str): The policy ID in watsonx.governance.
        inventory_id (str): The inventory ID in watsonx.governance.
        instance_id (str): The instance ID in watsonx.governance.
        region (Region, optional): The region where watsonx.governance is hosted when using IBM Cloud.
            Defaults to `us-south`.

    Example:
        ```python
        from novastack.guardrails.watsonx.supporting_classes.enums import Region

        from novastack.guardrails.watsonx import (
            WatsonxGuardrail,
        )

        # watsonx.governance (IBM Cloud)
        guardrails_manager = WatsonxGuardrail(
            api_key="API_KEY",
            policy_id="POLICY_ID",
            inventory_id="INVENTORY_ID",
            instance_id="INSTANCE_ID",
            region=Region.US_SOUTH,
        )
        ```
    """

    api_key: str = Field(..., description="The API key for IBM watsonx.governance")
    policy_id: str = Field(..., description="The policy ID in watsonx.governance")
    inventory_id: str = Field(..., description="The inventory ID in watsonx.governance")
    instance_id: str = Field(..., description="The instance ID in watsonx.governance")
    region: Region | str = Field(
        default=Region.US_SOUTH,
        description="The region where watsonx.governance is hosted when using IBM Cloud",
    )

    _token_manager: Any = PrivateAttr(default=None)

    def model_post_init(self, __context):  # noqa: PYI063
        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

        self.region = Region.from_value(self.region)
        authenticator = IAMAuthenticator(apikey=self.api_key)
        self._token_manager = authenticator.token_manager

    def _get_token(self) -> str:
        """Get authentication token."""
        return self._token_manager.get_token()

    def _http_post(
        self,
        url: str,
        path: str,
        payload: dict[str, Any],
        token: str | None = None,
        timeout: int = 10,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{url.rstrip('/')}/{path.lstrip('/')}"
        base_headers = {"Content-Type": "application/json"}

        # Add API token header if provided
        if token:
            base_headers["Authorization"] = f"Bearer {token}"

        # Merge custom headers
        if headers:
            base_headers.update(headers)

        try:
            response = requests.post(
                url, json=payload, headers=base_headers, timeout=timeout, params=params
            )
        except requests.RequestException as e:
            raise RuntimeError(
                f"Unable to complete the HTTP request. Underlying error: {str(e)}"  # noqa: RUF010
            ) from e

        if not response.ok:
            raise RuntimeError(
                f"Received unexpected HTTP status code {response.status_code}. "
                f"Service response: {response.text}"
            )

        return response.json()

    def enforce(
        self,
        text: str,
        direction: Direction | str,
        prompt_template: PromptTemplate | str | None = None,
        context: list = [],
    ) -> GuardrailResponse:
        """
        Runs policies enforcement to specified guardrail.

        Args:
            text (str): The input text that needs to be evaluated or processed according to the guardrail policy.
            direction (Direction): Whether the guardrail is processing the input or generated output.
            prompt_template (PromptTemplate, optional): The prompt template.
            context (list, optional): List of context.

        Example:
            ```python
            from novastack.guardrails.watsonx.supporting_classes.enums import Direction

            guardrails_manager.enforce(
                text="Hi, How can I help you?",
                direction=Direction.OUTPUT,
            )
            ```
        """
        prompt_template = PromptTemplate.from_value(prompt_template)
        direction = Direction.from_value(direction).value
        access_token = self._get_token()

        if direction == Direction.INPUT.value:
            detectors_properties = {
                "prompt_safety_risk": {"system_prompt": prompt_template.template},
                "topic_relevance": {"system_prompt": prompt_template.template},
            }
        if direction == Direction.OUTPUT.value:
            detectors_properties = {
                "groundedness": {"context_type": "docs", "context": context},
                "context_relevance": {"context_type": "docs", "context": context},
                "answer_relevance": {
                    "prompt": prompt_template.format(context="\n".join(context)),
                    "generated_text": text,
                },
            }

        payload = {
            "text": text,
            "direction": direction,
            "detectors_properties": detectors_properties,
        }

        response = self._http_post(
            url=self.region.openscale,
            path=f"/guardrails-manager/v1/enforce/{self.policy_id}",
            payload=payload,
            token=access_token,
            headers={"x-governance-instance-id": self.instance_id},
            params={"inventory_id": self.inventory_id},
        )

        return GuardrailResponse(
            text=response.get("entity", {}).get("text", ""),
            raw=response,
        )
