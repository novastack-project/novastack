from enum import Enum


class SimilarityMode(str, Enum):
    """Modes for similarity."""

    COSINE = "cosine"
    DOT_PRODUCT = "dot_product"
    EUCLIDEAN = "euclidean"
