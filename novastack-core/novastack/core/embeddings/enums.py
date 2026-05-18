from novastack.common.enums import BaseStrEnum


class SimilarityMode(BaseStrEnum):
    """Modes for similarity."""

    COSINE = "cosine"
    DOT_PRODUCT = "dot_product"
    EUCLIDEAN = "euclidean"
