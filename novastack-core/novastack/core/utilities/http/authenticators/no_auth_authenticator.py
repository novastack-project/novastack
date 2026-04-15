from novastack.core.utilities.http.authenticators.base import BaseAuthenticator


class NoAuthAuthenticator(BaseAuthenticator):
    """
    This is the default authentication when no authentication is required.
    It returns empty dict, adding no authentication headers to requests.
    """

    def authenticate(self) -> dict[str, str]:
        return {}
