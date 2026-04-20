from typing import Any

from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.guardrails import BaseGuardrail, GuardrailResponse
from novastack.core.guardrails.enums import Direction
from novastack.core.utilities.http import HttpService
from novastack.core.utilities.http.authenticators import IBMIAMAuthenticator
from novastack.guardrails.watsonx.supporting_classes.enums import Region


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
    region: Region = Field(
        default=Region.US_SOUTH,
        description="The region where watsonx.governance is hosted when using IBM Cloud",
    )

    _guardrail_manager: Any = PrivateAttr(default=None)

    def model_post_init(self, __context):  # noqa: PYI063
        self.region = Region.enum_validate(self.region)
        self._guardrail_manager = HttpService(
            base_url=self.region.openscale,
            timeout=10,
            headers={"x-governance-instance-id": self.instance_id},
            authenticator=IBMIAMAuthenticator(api_key=self.api_key),
        )

    def _get_policy_detectors(self) -> dict[str, Any]:
        result = self._guardrail_manager.get(
            url=f"/guardrails_manager/v2/policies/{self.policy_id}",
            params={"inventory_id": self.inventory_id},
        )

        entity = result.json_dump().get("entity", {})

        def _build_detectors_map(items):
            result = {}
            for item in items:
                detector_name = item.get("detector")
                if detector_name:
                    result[detector_name] = {}
            return result

        return {
            "input": _build_detectors_map(entity.get("input", [])),
            "output": _build_detectors_map(entity.get("output", [])),
        }

    def _validate_detector_requirements(
        self,
        direction: str,
        detectors: dict,
        prompt: str | None,
        context: list,
    ) -> None:
        """
        Validates that required parameters are provided based on the direction and active detectors.

        Args:
            direction (str): The direction value ("input" or "output").
            prompt (str | None): The system prompt.
            context (list): List of context documents.

        Raises:
            ValueError: If required parameters are missing for active detectors.
        """
        input_detectors = detectors.get("input", {})
        output_detectors = detectors.get("output", {})

        if direction == Direction.INPUT.value:
            # Check if prompt_safety_risk or topic_relevance detectors are active
            if (
                "prompt_safety_risk" in input_detectors
                or "topic_relevance" in input_detectors
            ):
                if prompt is None:
                    raise ValueError(
                        "'prompt' cannot be None when direction is 'input' and "
                        "'prompt_safety_risk' or 'topic_relevance' detectors are active in the policy"
                    )

        elif direction == Direction.OUTPUT.value:
            # Check if answer_relevance detector is active
            if "answer_relevance" in output_detectors:
                if prompt is None:
                    raise ValueError(
                        "'prompt' cannot be None when direction is 'output' and "
                        "'answer_relevance' detector is active in the policy"
                    )

            # Check if context_relevance or groundedness detectors are active
            if (
                "context_relevance" in output_detectors
                or "groundedness" in output_detectors
            ):
                if not context or context is None:
                    raise ValueError(
                        "context cannot be None or empty when direction is 'output' and "
                        "'context_relevance' or 'groundedness' detectors are active in the policy"
                    )

    def enforce(
        self,
        text: str,
        direction: Direction,
        prompt: str | None = None,
        context: list = [],
    ) -> GuardrailResponse:
        """
        Runs policies enforcement to specified guardrail.

        Args:
            text (str): The input text that needs to be evaluated or processed according to the guardrail policy.
            direction (Direction): Whether the guardrail is processing the input or generated output.
            prompt (str, optional): The prompt.
            context (list, optional): List of context.

        Example:
            ```python
            from novastack.core.guardrails.enums import Direction

            guardrails_manager.enforce(
                text="Hi, How can I help you?",
                direction=Direction.OUTPUT,
                prompt="You are a helpful assistant."
            )
            ```
        """
        direction = Direction.enum_validate(direction).value

        # Validate detector requirements before proceeding
        detectors = self._get_policy_detectors()
        self._validate_detector_requirements(
            direction, detectors, prompt, context
        )

        # Configure detector properties based on direction
        detector_configs: dict[str, dict[str, Any]] = {}

        if direction == Direction.INPUT.value:
            detector_configs = {
                "prompt_safety_risk": {"system_prompt": prompt}
                if prompt
                else {},
                "topic_relevance": {"system_prompt": prompt}
                if prompt
                else {},
            }
        else:  # Direction.OUTPUT.value
            detector_configs = {
                "groundedness": {"context_type": "docs", "context": context},
                "context_relevance": {"context_type": "docs", "context": context},
                "answer_relevance": {
                    "prompt": prompt
                    if prompt
                    else "",
                    "generated_text": text,
                },
            }

        # Apply detector properties for active detectors
        for detector_name, config in detector_configs.items():
            if detector_name in detectors[direction]:
                detectors[detector_name] = config

        response = self._guardrail_manager.post(
            url=f"/guardrails_manager/v2/enforce/{self.policy_id}",
            params={"inventory_id": self.inventory_id},
            json={
                "text": text,
                "direction": direction,
                "detectors_properties": detectors[direction],
            },
        )

        return GuardrailResponse(
            text=response.json_dump().get("entity", {}).get("text", ""),
            raw=response.json_dump(),
        )
