import os
import tempfile
from typing import Any

from novastack.core.bridge.pydantic import Field, PrivateAttr
from novastack.core.document import Document
from novastack.core.loaders import BaseLoader, DirectoryLoader


class IBMCOSLoader(BaseLoader):
    """
    IBM Cloud Object Storage bucket loader.

    Attributes:
        bucket (str): Name of the bucket.
        ibm_api_key_id (str, optional): IBM Cloud API key.
        ibm_service_instance_id (str, optional): Service instance ID for the IBM COS.
        s3_endpoint_url (str, optional): Endpoint for the IBM Cloud Object Storage service (S3 compatible).

    Example:
        ```python
        from novastack.loaders.ibm_cos import IBMCOSLoader

        cos_loader = IBMCOSLoader(
            bucket="your_bucket",
            ibm_api_key_id="your_api_key",
            ibm_service_instance_id="your_instance_id",
            s3_endpoint_url="your_api_url",
        )
        ```
    """

    bucket: str = Field(..., description="Name of the bucket")
    ibm_api_key_id: str | None = Field(default=None, description="IBM Cloud API key")
    ibm_service_instance_id: str | None = Field(
        default=None, description="Service instance ID for the IBM COS"
    )
    s3_endpoint_url: str | None = Field(
        default=None,
        description="Endpoint for the IBM Cloud Object Storage service (S3 compatible)",
    )

    _ibm_boto3: Any = PrivateAttr()
    _boto_config: Any = PrivateAttr()

    def model_post_init(self, __context):  # noqa: PYI063
        import ibm_boto3
        from ibm_botocore.client import Config

        self._ibm_boto3 = ibm_boto3
        self._boto_config = Config

    def load_data(self, input_file: str, **kwargs: Any) -> list[Document]:
        """Loads data from the specified bucket."""
        ibm_s3 = self._ibm_boto3.resource(
            "s3",
            ibm_api_key_id=self.ibm_api_key_id,
            ibm_service_instance_id=self.ibm_service_instance_id,
            config=self._boto_config(signature_version="oauth"),
            endpoint_url=self.s3_endpoint_url,
        )

        bucket = ibm_s3.Bucket(self.bucket)

        with tempfile.TemporaryDirectory() as temp_dir:
            for obj in bucket.objects.filter(Prefix=""):
                file_path = f"{temp_dir}/{obj.key}"
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                ibm_s3.meta.client.download_file(self.bucket, obj.key, file_path)

            # s3_source = re.sub(r"^(https?)://", "", self.s3_endpoint_url)

            return DirectoryLoader(input_dir=temp_dir).load_data()
