import logging
from typing import Any

from novastack.core.bridge.pydantic import SecretStr
from novastack.observability.watsonx.supporting_classes.credentials import (
    CloudPakforDataCredentials,
)
from novastack.observability.watsonx.supporting_classes.enums import Region
from novastack.observability.watsonx.utils.data_utils import validate_and_filter_dict


def process_cpd_credentials(
    cpd_creds: CloudPakforDataCredentials | dict,
) -> dict[str, dict]:
    """
    Args:
        cpd_creds: CloudPakforDataCredentials instance or dict with CPD credentials.
    """
    cpd_creds = CloudPakforDataCredentials.model_validate(cpd_creds)
    cpd_dict = cpd_creds.to_dict()

    # Process credentials for Watson OpenScale
    wos_creds = validate_and_filter_dict(
        original_dict=cpd_dict,
        optional_keys=[
            "username",
            "password",
            "api_key",
            "disable_ssl_verification",
        ],
        required_keys=["url"],
    )

    # Process credentials for AI Governance Facts
    fact_creds = validate_and_filter_dict(
        original_dict=cpd_dict,
        optional_keys=["username", "password", "api_key", "bedrock_url"],
        required_keys=["url"],
    )
    fact_creds["service_url"] = fact_creds.pop("url")

    # Process credentials for Watson Machine Learning
    wml_creds = validate_and_filter_dict(
        original_dict=cpd_dict,
        optional_keys=[
            "username",
            "password",
            "api_key",
            "instance_id",
            "version",
            "bedrock_url",
        ],
        required_keys=["url"],
    )

    return {
        "wos": wos_creds,
        "facts": fact_creds,
        "wml": wml_creds,
    }


class WosClientFactory:
    """Factory class for creating IBM Watson OpenScale API client."""

    @staticmethod
    def create_client(
        api_key: SecretStr | None = None,
        region: Region = Region.US_SOUTH,
        cpd_creds: CloudPakforDataCredentials | dict | None = None,
        service_instance_id: str | None = None,
    ) -> Any:
        """
        Create and return a Watson OpenScale API client.

        Args:
            api_key: The API key for IBM Cloud authentication.
            region: The region object containing service URLs.
            cpd_creds: CloudPakforDataCredentials instance or dict with CPD credentials.
            service_instance_id: The service instance ID.

        Returns:
            An initialized WosAPIClient instance.

        Raises:
            Exception: If connection to IBM watsonx.governance (openscale) fails.
        """
        from ibm_watson_openscale import APIClient as WosAPIClient  # type: ignore

        try:
            if cpd_creds:
                from ibm_cloud_sdk_core.authenticators import (
                    CloudPakForDataAuthenticator,  # type: ignore
                )

                wos_cpd_creds = process_cpd_credentials(cpd_creds)["wos"]

                authenticator = CloudPakForDataAuthenticator(**wos_cpd_creds)
                return WosAPIClient(
                    authenticator=authenticator,
                    service_url=wos_cpd_creds["url"],
                    service_instance_id=service_instance_id,
                )
            else:
                from ibm_cloud_sdk_core.authenticators import (
                    IAMAuthenticator,  # type: ignore
                )

                authenticator = IAMAuthenticator(apikey=api_key.get_secret_value())
                return WosAPIClient(
                    authenticator=authenticator,
                    service_url=region.openscale,
                    service_instance_id=service_instance_id,
                )

        except Exception as e:
            logging.error(
                f"Error connecting to IBM watsonx.governance (openscale): {e}",
            )
            raise


class AIGovFactsClientFactory:
    """Factory class for creating IBM AI Governance Facts API client."""

    @staticmethod
    def create_client(
        api_key: SecretStr | None = None,
        container_id: str | None = None,
        container_type: str | None = None,
        region: Region = Region.US_SOUTH,
        cpd_creds: CloudPakforDataCredentials | dict | None = None,
    ) -> Any:
        """
        Create and return an AI Governance Facts API client.

        Args:
            api_key: The API key for IBM Cloud authentication.
            container_id: The container ID (space_id or project_id).
            container_type: The container type ('space' or 'project').
            region: The region object containing service URLs.
            cpd_creds: CloudPakforDataCredentials instance or dict with CPD credentials.

        Returns:
            An initialized AIGovFactsClient instance.

        Raises:
            Exception: If connection to IBM watsonx.governance (factsheets) fails.
        """
        from ibm_aigov_facts_client import (  # type: ignore
            AIGovFactsClient,
            CloudPakforDataConfig,
        )

        try:
            if cpd_creds:
                fact_cpd_creds = process_cpd_credentials(cpd_creds)["facts"]

                cpd_config = CloudPakforDataConfig(**fact_cpd_creds)
                return AIGovFactsClient(
                    container_id=container_id,
                    container_type=container_type,
                    cloud_pak_for_data_configs=cpd_config,
                    disable_tracing=True,
                )
            else:
                return AIGovFactsClient(
                    api_key=api_key.get_secret_value(),
                    container_id=container_id,
                    container_type=container_type,
                    disable_tracing=True,
                    region=region.factsheet,
                )

        except Exception as e:
            logging.error(
                f"Error connecting to IBM watsonx.governance (factsheets): {e}",
            )
            raise


class WMLClientFactory:
    """Factory class for creating IBM Watson Machine Learning API client."""

    @staticmethod
    def create_client(
        api_key: SecretStr  | None = None,
        region: Region = Region.US_SOUTH,
        cpd_creds: CloudPakforDataCredentials | dict | None = None,
        space_id: str | None = None,
    ) -> Any:
        """
        Create and return a Watson Machine Learning API client.

        Args:
            api_key: The API key for IBM Cloud authentication.
            region: The region object containing service URLs.
            cpd_creds: CloudPakforDataCredentials instance or dict with CPD credentials.
            space_id: The space ID to set as default.

        Returns:
            An initialized APIClient instance with default space set.

        Raises:
            Exception: If connection to IBM watsonx.ai Runtime fails.
        """
        from ibm_watsonx_ai import APIClient, Credentials  # type: ignore

        try:
            if cpd_creds:
                wml_cpd_creds = process_cpd_credentials(cpd_creds)["wml"]

                authenticator = Credentials(**wml_cpd_creds)
                wml_client = APIClient(credentials=authenticator)

            else:
                authenticator = Credentials(
                    url=region.watsonx,
                    api_key=api_key.get_secret_value(),
                )
                wml_client = APIClient(credentials=authenticator)

            if space_id:
                wml_client.set.default_space(space_id)

            return wml_client

        except Exception as e:
            logging.error(f"Error connecting to IBM watsonx.ai Runtime: {e}")
            raise
