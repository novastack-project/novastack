from abc import ABC, abstractmethod

import numpy as np
from novastack.core.bridge.pydantic import BaseModel, Field
from novastack.core.document import Document
from novastack.core.embeddings.enums import SimilarityMode
from novastack.core.schema import TransformerComponent

Embedding = list[float]


def compute_similarity(
    embedding1: Embedding,
    embedding2: Embedding,
    mode: SimilarityMode = SimilarityMode.COSINE,
) -> float:
    """
    Calculate similarity between two embeddings.

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        mode: Similarity calculation mode (cosine, dot_product, or euclidean)
    """
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


class BaseEmbedding(BaseModel, TransformerComponent, ABC):
    """
    Abstract base class defining the interface for embedding models.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
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
        mode: SimilarityMode = SimilarityMode.COSINE,
    ):
        """Get embedding similarity."""
        return compute_similarity(embedding1, embedding2, mode)

    @abstractmethod
    def embed_text(self, input: str | list[str]) -> list[Embedding]:
        """
        Embed one or more text strings.

        Args:
            input: Single text string or list of text strings to embed
        """

    def embed_documents(self, documents: list[Document]) -> list[Document]:
        """
        Embed a list of documents and assign the computed embeddings to the 'embedding' attribute.

        Args:
            documents (list[Document]): List of documents to compute embeddings.
        """
        texts = [document.get_content() for document in documents]
        embeddings = self.embed_text(texts)

        for document, embedding in zip(documents, embeddings):
            document.embedding = embedding

        return documents

    def __call__(self, documents: list[Document]) -> list[Document]:
        return self.embed_documents(documents)
