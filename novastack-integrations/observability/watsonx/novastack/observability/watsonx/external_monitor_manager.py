import warnings

from novastack.observability.watsonx.aigov_client import WatsonxGovClient


class WatsonxExternalMonitorManager(WatsonxGovClient):
    """
    Deprecated: Use `WatsonxGovClient` with `setup_external_monitor()` instead.
    """

    def __init__(self, **data):
        warnings.warn(
            "WatsonxExternalMonitorManager is deprecated and will be removed in a future version. "
            "Use WatsonxGovClient with setup_external_monitor() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**data)

    def setup_monitor(
        self,
        name: str,
        model_id: str,
        model_provider: str,
        task_id: str,
        description: str = "",
        model_name: str | None = None,
        model_parameters: dict | None = None,
        model_url: str | None = None,
        prompt_id: str | None = None,
        prompt_url: str | None = None,
        prompt_additional_info: dict | None = None,
        prompt_template: str | None = None,
        prompt_variables: list[str] | None = None,
        locale: str = "en",
        context_fields: list[str] | None = None,
        question_field: str | None = None,
    ) -> dict:
        return self.setup_external_monitor(
            name=name,
            model_id=model_id,
            model_provider=model_provider,
            task_id=task_id,
            description=description,
            model_name=model_name,
            model_parameters=model_parameters,
            model_url=model_url,
            prompt_id=prompt_id,
            prompt_url=prompt_url,
            prompt_additional_info=prompt_additional_info,
            prompt_template=prompt_template,
            prompt_variables=prompt_variables,
            locale=locale,
            context_fields=context_fields,
            question_field=question_field,
        )


__all__ = ["WatsonxExternalMonitorManager"]
