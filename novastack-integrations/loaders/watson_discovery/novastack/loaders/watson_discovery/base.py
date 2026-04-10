from datetime import datetime
from logging import getLogger
from typing import Any

from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.document import Document
from novastack.core.loaders import BaseLoader

logger = getLogger(__name__)


class WatsonDiscoveryLoader(BaseLoader):
    """
    Provides functionality to read documents from IBM Watson Discovery.

    For more information, see
    [IBM Watson Discovery Getting Started](https://cloud.ibm.com/docs/discovery-data?topic=discovery-data-getting-started)

    Attributes:
        url (str): Watson Discovery instance URL.
        api_key (str): Watson Discovery API key.
        project_id (str): Watson Discovery project ID.
        version (str, optional): Watson Discovery API version. Defaults to `2023-03-31`.
        batch_size (int, optional): Batch size for bulk operations. Defaults to `50`.
        created_date (str, optional): Load documents created after this date.
            Expected format is `YYYY-MM-DD`. Defaults to today's date.
        pre_additional_data_field (str, optional): Additional data field to prepend to the Document content.
            Defaults to `None`.

    Example:
        ```python
        from novastack.loaders.watson_discovery import WatsonDiscoveryLoader

        discovery_loader = WatsonDiscoveryLoader(
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
    batch_size: int = Field(
        default=50, description="Batch size for bulk operations", ge=1
    )
    created_date: str = Field(
        default_factory=lambda: datetime.today().strftime("%Y-%m-%d"),
        description="Load documents created after this date (YYYY-MM-DD format)",
    )
    pre_additional_data_field: str | None = Field(
        default=None,
        description="Additional data field to prepend to the Document content",
    )

    _client: Any = PrivateAttr()

    def model_post_init(self, __context):  # noqa: PYI063
        """Initialize Watson Discovery client after Pydantic validation."""
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

    def load_data(self, input_file: str, **kwargs: Any) -> list[Document]:
        """
        Loads documents from Watson Discovery.

        Example:
            ```python
            docs = discovery_loader.load_data()
            ```
        """
        from ibm_watson.discovery_v2 import QueryLargePassages

        last_batch_size = self.batch_size
        offset_len = 0
        documents = []
        return_fields = [
            "extracted_metadata.filename",
            "extracted_metadata.file_type",
            "text",
        ]

        if self.pre_additional_data_field:
            return_fields.append(self.pre_additional_data_field)

        while last_batch_size == self.batch_size:
            results = self._client.query(
                project_id=self.project_id,
                count=self.batch_size,
                offset=offset_len,
                return_=return_fields,
                filter="extracted_metadata.publicationdate>={}".format(
                    self.created_date,
                ),
                passages=QueryLargePassages(enabled=False),
            ).get_result()

            last_batch_size = len(results["results"])
            offset_len = offset_len + last_batch_size

            # Make sure all retrieved document 'text' exist
            results_documents = [doc for doc in results["results"] if "text" in doc]

            if self.pre_additional_data_field:
                for i, doc in enumerate(results_documents):
                    doc["text"].insert(
                        0,
                        self._get_nested_value(doc, self.pre_additional_data_field),
                    )

            documents.extend(
                [
                    Document(
                        id_=doc["document_id"],
                        text="\n".join(doc["text"]),
                        metadata={
                            "collection_id": doc["result_metadata"]["collection_id"],
                        }
                        | doc["extracted_metadata"],
                    )
                    for doc in results_documents
                ],
            )

        return documents

    @staticmethod
    def _get_nested_value(d, key_path, separator: str | None = "."):
        """Accesses a nested value in a dictionary using a string key path."""
        keys = key_path.split(separator)  # Split the key_path using the separator
        nested_value = d

        for key in keys:
            nested_value = nested_value[key]  # Traverse the dictionary by each key

        return nested_value
