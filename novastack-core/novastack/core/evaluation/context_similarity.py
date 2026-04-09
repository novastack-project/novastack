from typing import Any

import numpy as np
from novastack.core.bridge.pydantic import (
    ConfigDict,
    Field,
)
from novastack.core.embeddings import BaseEmbedding, SimilarityMode
from novastack.core.evaluation.base import BaseEvaluator


class ContextSimilarityEvaluator(BaseEvaluator):
    """
    Evaluates context similarity using query-context and answer-context
    similarity combined with harmonic mean.

    This evaluator provides a balanced evaluation of RAG systems by ensuring:
    - **Retrieval quality**: How well contexts match the query (retrieval quality).
    - **Answer grounding**: How well the answer is supported by contexts (answer grounding).

    The harmonic mean is used to combine scores because it:
    - Penalizes imbalanced scores (both metrics must be good)
    - Is more conservative than arithmetic mean
    - Better reflects the "weakest link" in RAG quality

    Attributes:
        embed_model (BaseEmbedding): The embedding model used to compute vector representations.
        similarity_mode (SimilarityMode, optional): Similarity strategy to use. Supported options are
            `"cosine"`, `"dot_product"`, and `"euclidean"`. Defaults to `"cosine"`.
        score_threshold (float, optional): Minimum required score for evaluation approval.
            Must be between 0.0 and 1.0. Defaults to `0.8`.

    Example:
        ```python
        from novastack.core.evaluation import ContextSimilarityEvaluator
        from novastack.embedding.huggingface import HuggingFaceEmbedding

        embedding = HuggingFaceEmbedding()

        evaluator = ContextSimilarityEvaluator(embed_model=embedding)
        ```
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    embed_model: BaseEmbedding = Field(
        description="Embedding model used to compute vector representations"
    )
    similarity_mode: SimilarityMode = Field(
        default=SimilarityMode.COSINE,
        description="Similarity computation method",
    )

    def _calculate_similarity(
        self, reference_text: str, contexts: list[str]
    ) -> tuple[list[float], float]:
        """
        Calculate similarity scores between reference text and contexts.

        Args:
            reference_text: The text to compare against contexts (query or answer)
            contexts: List of context strings

        Returns:
            Tuple of (individual_scores, mean_score)
        """
        contexts_score: list[float] = []
        reference_embedding = self.embed_model.embed_text(reference_text)[0]

        for context in contexts:
            if not context or not context.strip():
                continue

            context_embedding = self.embed_model.embed_text(context)[0]
            score = self.embed_model.similarity(
                reference_embedding,
                context_embedding,
                mode=self.similarity_mode,
            )
            contexts_score.append(score)

        if not contexts_score:
            raise ValueError("Unable to evaluate: no valid contexts provided")

        mean_score = float(np.mean(contexts_score))
        return contexts_score, mean_score

    def _compute_harmonic_mean(self, query_score: float, answer_score: float) -> float:
        """
        Compute harmonic mean of query and answer scores.

        Args:
            query_score: Query-context similarity score
            answer_score: Answer-context similarity score

        Returns:
            Harmonic mean: 2 * (q * a) / (q + a)
        """
        if query_score + answer_score == 0:
            return 0.0
        return 2 * (query_score * answer_score) / (query_score + answer_score)

    def evaluate(
        self,
        query: str | None = None,
        generated_text: str | None = None,
        contexts: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Evaluate context similarity using query and answer.

        Args:
            query (str): Input query text
            generated_text (str): LLM-generated answer text
            contexts (list[str]): List of context strings
            **kwargs: Additional keyword arguments (unused)

        Returns:
            ```python
            {
                "query_context_similarity": {
                    "contexts_score": [0.92, 0.85],  # Individual scores per context
                    "score": 0.885                    # Mean query-context score
                },
                "answer_context_similarity": {
                    "contexts_score": [0.88, 0.82],  # Individual scores per context
                    "score": 0.850                    # Mean answer-context score
                },
                "score": 0.867,                       # Harmonic mean of both scores
                "passing": True,                      # Whether score >= threshold
            }
            ```

        Example:
            ```python
            result = evaluator.evaluate(
                query="What is the capital of France?",
                generated_text="The capital of France is Paris.",
                contexts=["Paris is the capital city of France.", "France is in Europe."]
            )

            print(f"Query-Context Score: {result['query_context_similarity']['score']}")
            print(f"Answer-Context Score: {result['answer_context_similarity']['score']}")
            print(f"Combined Score: {result['score']}")
            print(f"Passing: {result['passing']}")
            ```
        """
        del kwargs  # Unused

        # Validate all required parameters
        if not contexts:
            raise ValueError("Must provide 'contexts' parameter")
        if not query:
            raise ValueError("Must provide 'query' parameter")
        if not generated_text:
            raise ValueError("Must provide 'generated_text' parameter")

        # Calculate query-context similarity
        query_contexts_score, query_mean_score = self._calculate_similarity(
            query, contexts
        )

        # Calculate answer-context similarity
        answer_contexts_score, answer_mean_score = self._calculate_similarity(
            generated_text, contexts
        )

        # Combine scores using harmonic mean
        combined_score = self._compute_harmonic_mean(
            query_mean_score, answer_mean_score
        )

        # Determine passing status
        passing = combined_score >= self.score_threshold

        return {
            "query_context_similarity": {
                "contexts_score": query_contexts_score,
                "score": query_mean_score,
            },
            "answer_context_similarity": {
                "contexts_score": answer_contexts_score,
                "score": answer_mean_score,
            },
            "score": combined_score,
            "passing": passing,
        }
