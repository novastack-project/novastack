import logging
from typing import TYPE_CHECKING, Any

from donkey.core.toolkit import validate_type
from novastack.observability.watsonx.authenticators import (
    CloudPakForDataAuthenticator,
    IAMAuthenticator,
    MCSPV2Authenticator,
)
from novastack.observability.watsonx.enums import Region

if TYPE_CHECKING:
    from ibm_cloud_sdk_core.authenticators import Authenticator as IBMAuthenticator


class WosClientFactory:
    """Factory class for creating IBM Watson OpenScale API client."""

    @staticmethod
    def create_client(
        authenticator: "IBMAuthenticator",
        region: str = Region.US_SOUTH,
        service_instance_id: str | None = None,
    ) -> Any:
        """
        Create and return a Watson OpenScale API client.

        Args:
            authenticator: The authenticator specifies the authentication mechanism.
            region: The region object containing service URLs.
            service_instance_id: The service instance ID.
        """
        region = Region.from_value(region)

        from ibm_watson_openscale import APIClient as WosAPIClient  # type: ignore

        try:
            if isinstance(authenticator, CloudPakForDataAuthenticator):
                return WosAPIClient(
                    authenticator=authenticator._base_authenticator,
                    service_url=authenticator.base_url,
                    service_instance_id=service_instance_id,
                )
            else:
                return WosAPIClient(
                    authenticator=authenticator._base_authenticator,
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
        authenticator: "IBMAuthenticator",
        container_id: str | None = None,
        container_type: str | None = None,
        region: str = Region.US_SOUTH,
    ) -> Any:
        """
        Create and return an AI Governance Facts API client.

        Args:
            authenticator: The authenticator specifies the authentication mechanism.
            container_id: The container ID (space_id or project_id).
            container_type: The container type ('space' or 'project').
            region: The region object containing service URLs.
        """
        region = Region.from_value(region)
        EXPERIMENT_NAME = "novastack-aigov-experiment"

        from ibm_aigov_facts_client import AIGovFactsClient  # type: ignore

        try:
            if isinstance(authenticator, CloudPakForDataAuthenticator):
                return AIGovFactsClient(
                    experiment_name=EXPERIMENT_NAME,
                    authenticator=authenticator._base_authenticator,
                    container_id=container_id,
                    container_type=container_type,
                    set_as_current_experiment=True,
                    enable_autolog=False,
                    disable_tracing=True,
                )
            else:
                return AIGovFactsClient(
                    experiment_name=EXPERIMENT_NAME,
                    authenticator=authenticator._base_authenticator,
                    container_id=container_id,
                    container_type=container_type,
                    set_as_current_experiment=True,
                    enable_autolog=False,
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
        authenticator: "IBMAuthenticator",
        region: str = Region.US_SOUTH,
        space_id: str | None = None,
    ) -> Any:
        """
        Create and return a Watson Machine Learning API client.

        Args:
            authenticator: The authenticator specifies the authentication mechanism.
            region: The region object containing service URLs.
            space_id: The space ID to set as default.
        """
        region = Region.from_value(region)

        from ibm_watsonx_ai import APIClient, Credentials  # type: ignore

        allowed = [CloudPakForDataAuthenticator, IAMAuthenticator, MCSPV2Authenticator]

        validate_type(authenticator, "authenticator", allowed)

        try:
            if isinstance(authenticator, CloudPakForDataAuthenticator):
                credentials = Credentials(
                    url=authenticator.base_url,
                    username=authenticator.token_manager.username,
                    api_key=authenticator.token_manager.apikey,
                    password=authenticator.token_manager.password,
                    instance_id=authenticator.instance_id,
                    version=authenticator.version,
                )
                wml_client = APIClient(credentials=credentials)
            else:
                credentials = Credentials(
                    api_key=authenticator.token_manager.apikey, url=region.watsonx
                )
                wml_client = APIClient(credentials=credentials)

            if space_id:
                wml_client.set.default_space(space_id)

            return wml_client

        except Exception as e:
            logging.error(f"Error connecting to IBM watsonx.ai Runtime: {e}")
            raise
