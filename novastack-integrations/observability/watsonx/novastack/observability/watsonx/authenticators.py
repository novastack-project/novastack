from typing import Literal

from ibm_cloud_sdk_core.authenticators import (
    CloudPakForDataAuthenticator as _IBMCloudPakForDataAuthenticator,
)
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator, MCSPV2Authenticator


class CloudPakForDataAuthenticator(_IBMCloudPakForDataAuthenticator):
    """
    IBM Cloud Pak for Data Authenticator.

    Attributes:
        username (str, optional): The username for the environment.
        password (str, optional): The password for the environment.
        url (str): The host URL of the Cloud Pak for Data environment.
        apikey (str, optional): The API key for the environment, if IAM is enabled.
        disable_ssl_verification (bool, optional): Indicates whether to disable SSL certificate verification.
            Defaults to `False`.
        headers (str, optional): Default headers to be sent with every CP4D token request. Defaults to None.
        proxies (str, optional): Dictionary for mapping request protocol to proxy URL.
        verify (str, optional): The path to the certificate to use for HTTPS requests.
        instance_id (str, optional): The instance ID. Valid values are "icp" and "openshift".
        version (str, optional): The version of Cloud Pak for Data.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        url: str | None = None,
        *,
        apikey: str | None = None,
        disable_ssl_verification: bool = False,
        headers: dict[str, str] | None = None,
        proxies: dict[str, str] | None = None,
        verify: str | None = None,
        instance_id: Literal["icp", "openshift"] | None = None,
        version: str | None = None,
    ) -> None:
        self.instance_id = instance_id
        self.version = version

        super().__init__(
            username=username,  # type: ignore
            password=password,  # type: ignore
            url=url,  # type: ignore
            apikey=apikey,  # type: ignore
            disable_ssl_verification=disable_ssl_verification,
            headers=headers,
            proxies=proxies,
            verify=verify,
        )


__all__ = [
    "CloudPakForDataAuthenticator",
    "IAMAuthenticator",
    "MCSPV2Authenticator",
]
