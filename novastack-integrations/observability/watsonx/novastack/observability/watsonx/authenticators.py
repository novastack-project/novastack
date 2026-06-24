from typing import Literal

from ibm_cloud_sdk_core.authenticators import (
    CloudPakForDataAuthenticator as _IBMCloudPakForDataAuthenticator,
)
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator as _IAMAuthenticator
from ibm_cloud_sdk_core.authenticators import (
    MCSPV2Authenticator as _MCSPV2Authenticator,
)


class CloudPakForDataAuthenticator(_IBMCloudPakForDataAuthenticator):
    """
    IBM Cloud Pak for Data Authenticator.

    Attributes:
        url (str): The host URL of the Cloud Pak for Data environment.
        username (str, optional): The username for the environment.
        password (str, optional): The password for the environment.
        api_key (str, optional): The API key for the environment, if IAM is enabled.
        disable_ssl_verification (bool, optional): Indicates whether to disable SSL certificate verification.
            Defaults to `False`.
        headers (dict[str, str], optional): Default headers to be sent with every CP4D token request. Defaults to None.
        proxies (dict[str, str], optional): Dictionary for mapping request protocol to proxy URL.
        verify (str, optional): The path to the certificate to use for HTTPS requests.
        instance_id (str, optional): The instance ID. Valid values are "icp" and "openshift".
        version (str, optional): The version of Cloud Pak for Data.
    """

    def __init__(
        self,
        url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
        disable_ssl_verification: bool = False,
        headers: dict[str, str] | None = None,
        proxies: dict[str, str] | None = None,
        verify: str | None = None,
        instance_id: Literal["icp", "openshift"] = "openshift",
        version: str | None = None,
    ) -> None:
        base_kwargs = {
            "username": username,
            "password": password,
            "url": url,
            "apikey": api_key,
            "disable_ssl_verification": disable_ssl_verification,
            "headers": headers,
            "proxies": proxies,
            "verify": verify,
        }

        self.base_url = url
        self.instance_id = instance_id
        self.version = version

        self._base_authenticator = _IBMCloudPakForDataAuthenticator(**base_kwargs)
        super().__init__(**base_kwargs)


class IAMAuthenticator(_IAMAuthenticator):
    """
    IBM IAMAuthenticator Authenticator.

    Attributes:
        api_key (str): The IAM api key.
        url (str, optional): The URL representing the IAM token service endpoint. If not specified, a suitable default value is used.
        client_id (str, optional): The client_id and client_secret fields are used to form
            a "basic" authorization header for IAM token requests. Defaults to None.
        client_secret (str, optional): The client_id and client_secret fields are used to form
            a "basic" authorization header for IAM token requests. Defaults to None.
        disable_ssl_verification (bool, optional): A flag that indicates whether verification of
        the server's SSL certificate should be disabled or not. Defaults to False.
        headers (dict, optional): Default headers to be sent with every IAM token request. Defaults to None.
        proxies (dict, optional): Dictionary for mapping request protocol to proxy URL. Defaults to None.
        scope (str, optional): The "scope" to use when fetching the bearer token from the IAM token server.
        This can be used to obtain an access token with a specific scope.
    """

    def __init__(
        self,
        api_key: str,
        *,
        url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        disable_ssl_verification: bool = False,
        headers: dict[str, str] | None = None,
        proxies: dict[str, str] | None = None,
        scope: str | None = None,
    ) -> None:
        base_kwargs = {
            "apikey": api_key,
            "url": url,
            "client_id": client_id,
            "client_secret": client_secret,
            "disable_ssl_verification": disable_ssl_verification,
            "headers": headers,
            "proxies": proxies,
            "scope": scope,
        }

        self._base_authenticator = _IAMAuthenticator(**base_kwargs)
        super().__init__(**base_kwargs)


class MCSPV2Authenticator(_MCSPV2Authenticator):
    """
    IBM MCSPV2Authenticator Authenticator.

    Attributes:
        api_key (str): The apikey used to obtain an access token.
        url (str): The base endpoint URL for the MCSP token service.
        scope_collection_type (Literal["accounts", "subscriptions", "services"]): The scope collection type of item(s).
        scope_id (str): The scope identifier of item(s).
        include_builtin_actions (bool, optional): A flag to include builtin actions in the "actions" claim in the
            MCSP access token (default: False).
        include_custom_actions (bool, optional): A flag to include custom actions in the "actions" claim in the
            MCSP access token (default: False).
        include_roles (bool, optional): A flag to include the "roles" claim in the MCSP access token (default: True).
        prefix_roles (bool, optional): A flag to add a prefix with the scope level where the role is defined
            in the "roles" claim (default: False).
        caller_ext_claim (dict, optional): A map (dictionary) containing keys and values to be injected into
            the access token as the "callerExt" claim (default: None).
            The keys used in this map must be enabled in the apikey by setting the
            "callerExtClaimNames" property when the apikey is created.
            This property is typically only used in scenarios involving an apikey with identityType `SERVICEID`.
        disable_ssl_verification (bool, optional):  A flag that indicates whether verification of the server's SSL
            certificate should be disabled or not (default: False).
        headers (dict, optional): Default headers to be sent with every MCSP token request (default: None).
        proxies (dict, optional): Dictionary for mapping request protocol to proxy URL (default: None).
    """

    def __init__(
        self,
        *,
        api_key: str,
        url: str,
        scope_collection_type: Literal["accounts", "subscriptions", "services"],
        scope_id: str,
        include_builtin_actions: bool = False,
        include_custom_actions: bool = False,
        include_roles: bool = True,
        prefix_roles: bool = False,
        caller_ext_claim: dict[str, str] | None = None,
        disable_ssl_verification: bool = False,
        headers: dict[str, str] | None = None,
        proxies: dict[str, str] | None = None,
    ) -> None:
        base_kwargs = {
            "apikey": api_key,
            "url": url,
            "scope_collection_type": scope_collection_type,
            "scope_id": scope_id,
            "include_builtin_actions": include_builtin_actions,
            "include_custom_actions": include_custom_actions,
            "include_roles": include_roles,
            "prefix_roles": prefix_roles,
            "caller_ext_claim": caller_ext_claim,
            "disable_ssl_verification": disable_ssl_verification,
            "headers": headers,
            "proxies": proxies,
        }

        self._base_authenticator = _MCSPV2Authenticator(**base_kwargs)
        super().__init__(**base_kwargs)


__all__ = [
    "CloudPakForDataAuthenticator",
    "IAMAuthenticator",
    "MCSPV2Authenticator",
]
