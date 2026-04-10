from typing import Any, Literal

from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.embeddings import BaseEmbedding, Embedding


class HuggingFaceEmbedding(BaseEmbedding):
    """
    HuggingFace `sentence_transformers` embedding models.

    Attributes:
        model_name (str): Hugging Face model to be used. Defaults to `sentence-transformers/all-MiniLM-L6-v2`.
        device (str, optional): Device to run the model on. Supports `cpu` and `cuda`. Defaults to `cpu`.

    Example:
        ```python
        from novastack.embeddings.huggingface import HuggingFaceEmbedding

        embedding = HuggingFaceEmbedding()
        ```
    """

    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Name of the embedding model",
    )
    device: Literal["cpu", "cuda"] = "cpu"

    _client: Any = PrivateAttr()

    def model_post_init(self, __context):  # noqa: PYI063
        from sentence_transformers import SentenceTransformer

        self._client = SentenceTransformer(self.model_name, device=self.device)

    def embed_text(self, input: str | list[str]) -> list[Embedding]:
        """
        Embed one or more text strings.

        Args:
            input (list[str]): Input for which to compute embeddings.
        """
        embeddings = self._client.encode_document(input).tolist()

        if embeddings and all(isinstance(item, list) for item in embeddings):
            return embeddings
        else:
            return [embeddings]
