from typing import Any

from novastack.core.bridge.pydantic import field_validator
from novastack.core.document import Document
from novastack.core.text_chunkers.base import BaseTextChunker
from novastack.core.text_chunkers.utils import (
    merge_splits,
    split_by_char,
    split_by_fns,
    split_by_regex,
    split_by_sentence_tokenizer,
    split_by_sep,
    tokenizer,
)


class SentenceChunker(BaseTextChunker):
    """
    Designed to split input text into smaller chunks, particularly useful for processing
    large documents or texts. Tries to keep sentences and paragraphs together.

    Attributes:
        chunk_size (int, optional): Size of each chunk. Default is `512`.
        chunk_overlap (int, optional): Amount of overlap between chunks. Default is `256`.
        separator (str, optional): Separator used for splitting text. Default is `" "`.

    Example:
        ```python
        from novastack.core.text_chunker import SentenceChunker

        text_chunker = SentenceChunker()
        ```
    """

    chunk_size: int = 512
    chunk_overlap: int = 256
    separator: str = " "

    @field_validator("chunk_overlap")
    @classmethod
    def _validate_chunk_overlap(cls, v: int, info: Any) -> int:
        chunk_size = info.data.get("chunk_size", 512)
        if v > chunk_size:
            raise ValueError(
                f"Got a larger `chunk_overlap` ({v}) than `chunk_size` "
                f"({chunk_size}). `chunk_overlap` should be smaller."
            )
        return v

    def model_post_init(self, __context):  # noqa: PYI063
        self._split_fns = [split_by_sep("\n\n\n"), split_by_sentence_tokenizer()]
        self._sub_split_fns = [
            split_by_regex("[^,.;？！]+[,.;？！]?"),
            split_by_sep(self.separator),
            split_by_char(),
        ]

    def chunk_text(self, text: str) -> list[str]:
        """
        Split a single string of text into smaller chunks.

        Args:
            text (str): Input text to split.

        Returns:
            list[str]: List of text chunks.

        Example:
            ```python
            chunks = text_chunker.chunk_text(
                "novastack is a data framework to load any data in one line of code and connect with AI applications."
            )
            ```
        """
        splits = self._split(text)

        return merge_splits(splits, self.chunk_size, self.chunk_overlap)

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

    def _split(self, text: str) -> list[dict]:
        text_len = len(tokenizer(text))
        if text_len <= self.chunk_size:
            return [{"text": text, "is_sentence": True, "token_size": text_len}]

        text_splits = []
        text_splits_by_fns, is_sentence = split_by_fns(
            text,
            self._split_fns,
            self._sub_split_fns,
        )

        for text_split_by_fns in text_splits_by_fns:
            split_len = len(tokenizer(text_split_by_fns))
            if split_len <= self.chunk_size:
                text_splits.append(
                    {
                        "text": text_split_by_fns,
                        "is_sentence": is_sentence,
                        "token_size": split_len,
                    },
                )
            else:
                recursive_text_splits = self._split(text_split_by_fns)
                text_splits.extend(recursive_text_splits)

        return text_splits
