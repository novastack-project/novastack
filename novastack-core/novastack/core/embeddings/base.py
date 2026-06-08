from abc import abstractmethod

import numpy as np
from novastack.core.base.enums import SimilarityMode
from novastack.core.base.schema import TransformerComponent
from novastack.core.bridge.pydantic import Field
from novastack.core.document import Document
from novastack.core.telemetry import DispatcherSpanMixin, get_dispatcher
from novastack.core.telemetry.events.embedding import (
    EmbeddingEndEvent,
    EmbeddingStartEvent,
)
from novastack.core.utils import validate_enum

dispatcher = get_dispatcher(__name__)
Embedding = list[float]


def similarity(
    embedding1: Embedding,
    embedding2: Embedding,
    mode: str = SimilarityMode.COSINE,
) -> float:
    """
    Calculate similarity between two embeddings.

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        mode: Similarity calculation mode (cosine, dot_product, or euclidean)
    """
    validate_enum(el=mode, el_name="mode", expected_enum=SimilarityMode)
    # Validate embeddings are not empty
    if len(embedding1) == 0 or len(embedding2) == 0:
        raise ValueError("Embeddings cannot be empty")

    # Validate embeddings have same dimension
    if len(embedding1) != len(embedding2):
        raise ValueError(
            f"Embeddings must have same dimension. "
            f"Got {len(embedding1)} and {len(embedding2)}"
        )

    if mode == SimilarityMode.EUCLIDEAN:
        return -float(np.linalg.norm(np.array(embedding1) - np.array(embedding2)))

    elif mode == SimilarityMode.DOT_PRODUCT:
        return float(np.dot(embedding1, embedding2))

    else:
        # Cosine similarity calculation
        X = np.array(embedding1)
        Y = np.array(embedding2)
        product = np.dot(X, Y)
        norm = np.linalg.norm(X) * np.linalg.norm(Y)
        return float(product / norm)


class BaseEmbedding(TransformerComponent, DispatcherSpanMixin):
    """
    Abstract base class defining the interface for embedding models.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    model_name: str = Field(..., description="Name of the embedding model")

    @classmethod
    def class_name(cls) -> str:
        return "BaseEmbedding"

    @staticmethod
    def similarity(
        embedding1: Embedding,
        embedding2: Embedding,
        mode: str = SimilarityMode.COSINE,
    ):
        """Get embedding similarity."""
        return similarity(embedding1, embedding2, mode)

    @abstractmethod
    def _get_text_embeddings(self, input: str | list[str]) -> list[Embedding]:
        """Embed one or more text strings."""

    @dispatcher.span
    def get_text_embeddings(self, input: str | list[str]) -> list[Embedding]:
        """
        Embed one or more text strings.

        Args:
            input: Single text string or list of text strings to embed
        """
        config_dict = self.model_dump(exclude={"api_key"})
        dispatcher.event(
            EmbeddingStartEvent(
                config_dict=config_dict,
            )
        )

        embeddings = self._get_text_embeddings(input)

        dispatcher.event(
            EmbeddingEndEvent(
                embeddings=embeddings,
            )
        )
        return embeddings

    @dispatcher.span
    def get_document_embeddings(self, documents: list[Document]) -> list[Document]:
        """
        Embed a list of documents and assign the computed embeddings to the 'embedding' attribute.

        Args:
            documents (list[Document]): List of documents to compute embeddings.
        """
        config_dict = self.model_dump(exclude={"api_key"})
        dispatcher.event(
            EmbeddingStartEvent(
                config_dict=config_dict,
            )
        )

        texts = [document.get_content() for document in documents]
        embeddings = self._get_text_embeddings(texts)

        for document, embedding in zip(documents, embeddings):
            document.embedding = embedding

        config_dict = self.model_dump(exclude={"api_key"})

        dispatcher.event(
            EmbeddingEndEvent(
                embeddings=embeddings,
            )
        )
        return documents

    def __call__(self, documents: list[Document]) -> list[Document]:
        return self.get_document_embeddings(documents)
