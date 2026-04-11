import uuid
from logging import getLogger
from typing import Any, Literal

from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.document import Document, DocumentWithScore
from novastack.core.embeddings import BaseEmbedding
from novastack.core.vector_stores import BaseVectorStore

logger = getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """
    Chroma is the AI-native open-source vector database.
    Embeddings are stored within a ChromaDB collection.

    Attributes:
        embed_model (BaseEmbedding): Embedding model used to compute vectors.
        collection_name (str, optional): Name of the ChromaDB collection.
        distance_strategy (str, optional): Distance strategy for similarity search.
            Currently supports `"cosine"`, `"ip"`, and `"l2"`. Defaults to `cosine`.

    Example:
        ```python
        from novastack.embeddings.huggingface import HuggingFaceEmbedding
        from novastack.vector_stores.chroma import ChromaVectorStore

        embedding = HuggingFaceEmbedding()
        vector_db = ChromaVectorStore(embed_model=embedding)
        ```
    """

    embed_model: BaseEmbedding = Field(
        ..., description="Embedding model used to compute vectors"
    )
    collection_name: str | None = Field(
        default=None, description="Name of the ChromaDB collection"
    )
    distance_strategy: Literal["cosine", "ip", "l2"] = Field(
        default="cosine",
        description="Distance strategy for similarity search (cosine, ip, or l2)",
    )

    _client_settings: Any = PrivateAttr()
    _client: Any = PrivateAttr()
    _collection: Any = PrivateAttr()

    def model_post_init(self, __context):  # noqa: PYI063
        import chromadb
        import chromadb.config

        self._client_settings = chromadb.config.Settings()
        self._client = chromadb.Client(self._client_settings)

        collection_name = self.collection_name
        if collection_name is None:
            collection_name = "auto-generated-" + str(uuid.uuid4())[:8]
            logger.info(f"collection_name: {collection_name}")

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
            metadata={"hnsw:space": self.distance_strategy},
        )

    def add_documents(self, documents: list[Document]) -> list:
        """
        Add documents to the ChromaDB collection.

        Args:
            documents (list[Document]): List of documents to add to the collection.
        """
        embeddings = []
        metadatas = []
        ids = []
        chroma_documents = []

        for doc in documents:
            metadatas.append({**doc.metadata, "hash": doc.hash})

            embeddings.append(
                doc.embedding
                if doc.embedding
                else self.embed_model.embed_text(doc.get_content()),
            )
            ids.append(doc.id_ if doc.id_ else str(uuid.uuid4()))
            chroma_documents.append(doc.get_content())

        self._collection.add(
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
            documents=chroma_documents,
        )

        return ids

    def query_documents(self, query: str, top_k: int = 4) -> list[DocumentWithScore]:
        """
        Performs a similarity search for the top-k most similar documents.

        Args:
            query (str): Query text.
            top_k (int, optional): Number of top results to return. Defaults to `4`.

        Returns:
            list[DocumentWithScore]: List of the most similar documents.
        """
        query_embedding = self.embed_model.embed_text(query)

        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
        )

        return [
            DocumentWithScore(
                document=Document(id_=result[0], text=result[1], metadata=result[2]),
                score=result[3],
            )
            for result in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def delete_documents(self, ids: list[str]) -> None:
        """
        Delete documents from the ChromaDB collection.

        Args:
            ids (list[str], optional): List of `Document` IDs to delete. Defaults to `None`.
        """
        self._collection.delete(ids=ids)

    def get_all_documents(
        self, include_fields: list[str] | None = None
    ) -> list[Document]:
        """Get all documents from vector store."""
        default_fields = ["documents", "metadatas", "embeddings"]
        include = include_fields if include_fields else default_fields
        field_map = {
            "ids": "_id",
            "documents": "text",
            "metadatas": "metadata",
            "embeddings": "embedding",
        }

        data = self._collection.get(include=include)
        num_items = len(data["ids"])

        return [
            Document(
                **{
                    mapped_key: data[original_key][i]
                    for original_key, mapped_key in field_map.items()
                },
            )
            for i in range(num_items)
        ]
