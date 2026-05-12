from novastack.core.base.enum import BaseStrEnum


class SimilarityMode(BaseStrEnum):
    """Modes for similarity."""

    COSINE = "cosine"
    DOT_PRODUCT = "dot_product"
    EUCLIDEAN = "euclidean"
