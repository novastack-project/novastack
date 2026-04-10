from typing import Any

from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.embeddings import BaseEmbedding, Embedding


class WatsonxEmbedding(BaseEmbedding):
    """
    IBM watsonx embedding models.

    Note:
            One of these parameters is required: `project_id` or `space_id`. Not both.

    See [https://cloud.ibm.com/apidocs/watsonx-ai#endpoint-url](https://cloud.ibm.com/apidocs/watsonx-ai#endpoint-url) for the watsonx.ai API endpoints.

    Attributes:
        model_name (str): IBM watsonx.ai model to be used. Defaults to `ibm/slate-30m-english-rtrvr`.
        api_key (str): watsonx API key.
        url (str): watsonx instance url.
        truncate_input_tokens (str): Maximum number of input tokens accepted. Defaults to `512`
        project_id (str, optional): watsonx project_id.
        space_id (str, optional): watsonx space_id.

    Example:
        ```python
        from novastack.embeddings.watsonx import WatsonxEmbedding

        watsonx_embedding = WatsonxEmbedding(
            api_key="your_api_key",
            url="your_instance_url",
            project_id="your_project_id",
        )
        ```
    """

    model_name: str = Field(
        default="ibm/slate-30m-english-rtrvr",
        description="Name of the embedding model",
    )
    api_key: str
    url: str
    truncate_input_tokens: int = 512
    project_id: str | None = None
    space_id: str | None = None

    _client: Any = PrivateAttr()

    def model_post_init(self, __context):  # noqa: PYI063
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import Embeddings as WatsonxEmbeddings

        if (not (self.project_id or self.space_id)) or (
            self.project_id and self.space_id
        ):
            raise ValueError(
                "Must provide ONE of these parameters [`project_id`, `space_id`], not both.",
            )

        kwargs_params = {
            "model_id": self.model_name,
            "params": {
                "truncate_input_tokens": self.truncate_input_tokens,
                "return_options": {"input_text": False},
            },
            "credentials": Credentials(api_key=self.api_key, url=self.url),
        }

        if self.project_id:
            kwargs_params["project_id"] = self.project_id
        else:
            kwargs_params["space_id"] = self.space_id

        self._client = WatsonxEmbeddings(**kwargs_params)

    def embed_text(self, input: str | list[str]) -> list[Embedding]:
        """
        Embed one or more text strings.

        Args:
            input (str | list[str]): Input for which to compute embeddings.
        """
        if isinstance(input, str):
            return [self._client.embed_query(input)]

        elif isinstance(input, list) and all(isinstance(i, str) for i in input):
            return self._client.embed_documents(input)
        else:
            raise TypeError(f"Expected str or list[str], got {type(input).__name__}")
