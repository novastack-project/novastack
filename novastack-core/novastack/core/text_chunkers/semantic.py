import re
from typing import Literal

import numpy as np
from novastack.core.document import Document
from novastack.core.embeddings import BaseEmbedding
from novastack.core.embeddings.base import compute_similarity
from novastack.core.embeddings.enums import SimilarityMode
from novastack.core.text_chunkers.base import BaseTextChunker


class SemanticChunker(BaseTextChunker):
    """
    Python class designed to split text into chunks using semantic understanding.

    Credit to Greg Kamradt's notebook:
    [5 Levels Of Text Splitting](https://github.com/FullStackRetrieval-com/RetrievalTutorials/blob/main/tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb)

    Attributes:
        embed_model (BaseEmbedding): Embedding model used for semantic chunking.
        buffer_size (int, optional): Number of sentences to group together. Default is `1`.
        breakpoint_threshold_amount (int, optional): Threshold percentage for detecting breakpoints between group of sentences.
            The smaller this number is, the more chunks will be generated. Default is `95`.
        device (str, optional): Device to use for processing. Currently supports "cpu" and "cuda". Default is `cpu`.

    Example:
        ```python
        from novastack.core.text_chunker import SemanticChunker
        from novastack.embedding.huggingface import HuggingFaceEmbedding

        embedding = HuggingFaceEmbedding()
        text_chunker = SemanticChunker(embed_model=embedding)
        ```
    """

    embed_model: BaseEmbedding
    buffer_size: int = 1
    breakpoint_threshold_amount: int = 95
    device: Literal["cpu", "cuda"] = "cpu"

    def _combine_sentences(self, sentences: list[dict]) -> list[dict]:
        """Combine sentences with neighbors based on buffer size."""
        for i in range(len(sentences)):
            combined_sentence = ""

            # Add previous sentences based on buffer size
            for j in range(i - self.buffer_size, i):
                if j >= 0:
                    combined_sentence += sentences[j]["sentence"] + " "

            # Add the current sentence
            combined_sentence += sentences[i]["sentence"]

            # Add next sentences based on buffer size
            for j in range(i + 1, i + 1 + self.buffer_size):
                if j < len(sentences):
                    combined_sentence += " " + sentences[j]["sentence"]

            sentences[i]["combined_sentence"] = combined_sentence

        return sentences

    def _calculate_cosine_distances(
        self,
        single_sentences_list: list[str],
    ) -> tuple[list[float], list[dict]]:
        _sentences = [
            {"sentence": x, "index": i} for i, x in enumerate(single_sentences_list)
        ]

        sentences = self._combine_sentences(_sentences)
        embeddings = self.embed_model.embed_text(
            [x["combined_sentence"] for x in sentences],
        )

        for i, sentence in enumerate(sentences):
            sentence["combined_sentence_embedding"] = embeddings[i]

        distances = []
        for i in range(len(sentences) - 1):
            embedding_current = sentences[i]["combined_sentence_embedding"]
            embedding_next = sentences[i + 1]["combined_sentence_embedding"]

            similarity_score = compute_similarity(
                embedding_current, embedding_next, SimilarityMode.COSINE
            )

            distance = 1 - similarity_score
            distances.append(distance)

            # Store distance in the dictionary
            sentences[i]["distance_to_next"] = distance

        return distances, sentences

    def _calculate_breakpoint(self, distances: list[float]) -> list:
        distance_threshold = np.percentile(distances, self.breakpoint_threshold_amount)

        return [i for i, x in enumerate(distances) if x > distance_threshold]

    def chunk_text(self, text: str) -> list[str]:
        """
        Split a single string of text into smaller chunks.

        Args:
            text (str): Input text to split.

        Returns:
            list[str]: List of text chunks.
        """
        single_sentences_list = re.split(r"(?<=[.?!])\s+", text)
        distances, sentences = self._calculate_cosine_distances(single_sentences_list)

        indices_above_thresh = self._calculate_breakpoint(distances)

        chunks = []
        start_index = 0

        for index in indices_above_thresh:
            # Slice the sentence_dicts from the current start index to the end index
            group = sentences[start_index : index + 1]
            combined_text = " ".join([d["sentence"] for d in group])
            chunks.append(combined_text)

            # Update the start index for the next group
            start_index = index + 1

        # The last group, if any sentences remain
        if start_index < len(sentences):
            combined_text = " ".join([d["sentence"] for d in sentences[start_index:]])
            chunks.append(combined_text)

        return chunks

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """
        Split a list of documents into smaller document chunks.

        Args:
            documents (list[Document]): List of `Document` objects to split.

        Returns:
            list[Document]: List of chunked documents objects.
        """
        chunks = []

        for document in documents:
            texts = self.chunk_text(document.get_content())
            metadata = {**document.metadata}

            for text in texts:
                if len(texts) > 1:
                    metadata["ref_doc_id"] = document.id_
                    metadata["ref_doc_hash"] = document.hash

                chunks.append(
                    Document(
                        text=text,
                        metadata=metadata,
                    ),
                )

        return chunks
