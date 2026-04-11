from logging import getLogger
from typing import Any

from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.document import Document, DocumentWithScore
from novastack.core.retrievers import BaseRetriever

logger = getLogger(__name__)


class WatsonDiscoveryRetriever(BaseRetriever):
    """
    Provides functionality to interact with IBM Watson Discovery for querying documents.

    For more information, see
    [IBM Watson Discovery Getting Started](https://cloud.ibm.com/docs/discovery-data?topic=discovery-data-getting-started)

    Attributes:
        url (str): Watson Discovery instance URL.
        api_key (str): Watson Discovery API key.
        project_id (str): Watson Discovery project ID.
        version (str, optional): Watson Discovery API version. Defaults to `2023-03-31`.
        disable_passages (bool, optional): Return the full document instead of passages.
            Only enable this if all documents are short. Defaults to `False`.

    Example:
        ```python
        from novastack.retrievers.watson_discovery import WatsonDiscoveryRetriever

        doc_retriever = WatsonDiscoveryRetriever(
            url="your_url", api_key="your_api_key", project_id="your_project_id"
        )
        ```
    """

    url: str = Field(..., description="Watson Discovery instance URL")
    api_key: str = Field(..., description="Watson Discovery API key")
    project_id: str = Field(..., description="Watson Discovery project ID")
    version: str = Field(
        default="2023-03-31", description="Watson Discovery API version"
    )
    disable_passages: bool = Field(
        default=False,
        description="Return the full document instead of passages. Only enable this if all documents are short",
    )

    _client: Any = PrivateAttr()

    def model_post_init(self, __context):  # noqa: PYI063
        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
        from ibm_watson import DiscoveryV2

        try:
            authenticator = IAMAuthenticator(self.api_key)
            self._client = DiscoveryV2(
                authenticator=authenticator, version=self.version
            )
            self._client.set_service_url(self.url)
        except Exception as e:
            logger.error(f"Error connecting to IBM Watson Discovery: {e}")
            raise

    def query_documents(
        self, query: str, filter: str | None = None, top_k: int = 4, **kwargs: Any
    ) -> list[DocumentWithScore]:
        """
        Search your data in the Discovery API and return a list of documents.

        Args:
            query (str): Query text.
            filter (str, optional): Searches for documents that match the filter.
                Use Discovery Query Language syntax. Defaults to `None`.
            top_k (int, optional): Number of top results to return. Defaults to `4`.

        Example:
            ```python
            docs = doc_retriever.query_documents("What's novastack Framework?")
            ```
        """
        from ibm_watson.discovery_v2 import QueryLargePassages

        return_fields = ["extracted_metadata.filename", "extracted_metadata.file_type"]

        if not self.disable_passages:
            return_fields.append("passages")
        else:
            return_fields.append("text")

        discovery_results = self._client.query(
            project_id=self.project_id,
            natural_language_query=query,
            count=top_k,
            return_=return_fields,
            filter=filter,
            passages=QueryLargePassages(
                enabled=not self.disable_passages,
                per_document=False,
                count=top_k,
                find_answers=False,
                characters=600,
            ),
        ).get_result()

        docs_and_scores = []

        if not self.disable_passages and len(discovery_results["passages"]) > 0:
            # If not `disable_passages`, always use discovery passages (recommended)
            for passage in discovery_results["passages"]:
                document_id_target = passage["document_id"]
                document = [
                    doc
                    for doc in discovery_results["results"]
                    if doc["document_id"] == document_id_target
                ]

                docs_and_scores.append(
                    DocumentWithScore(
                        document=Document(
                            text=passage["passage_text"],
                            metadata={"collection_id": passage["collection_id"]}
                            | document[0]["extracted_metadata"],
                        ),
                        score=passage["passage_score"] / 100,
                    ),
                )

        elif discovery_results["matching_results"] > 0:
            # If `disable_passages`, use document text (not recommended,
            # make sure that all documents are short to not exceed the model context window)
            logger.warning(
                "Not recommended to disable passages. "
                "Make sure that all documents are short to not exceed the model context window.",
            )
            for document in discovery_results["results"]:
                docs_and_scores.append(
                    DocumentWithScore(
                        document=Document(
                            text=" ".join(document["text"]),
                            metadata={
                                "collection_id": document["result_metadata"][
                                    "collection_id"
                                ],
                            }
                            | document["extracted_metadata"],
                        ),
                        score=document["result_metadata"]["confidence"],
                    ),
                )

        return docs_and_scores
