import base64

from novastack.core.bridge.pydantic import Field, SecretStr
from novastack.core.utilities.http.authenticators.base import BaseAuthenticator
from novastack.core.utilities.http.exceptions import HttpAuthenticationError


class BasicAuthenticator(BaseAuthenticator):
    """
    HTTP Basic Authentication.

    Implements standard HTTP Basic authentication using Base64 encoding
    of username and password credentials.
    """

    username: str = Field(..., min_length=1, description="Username for authentication")
    password: SecretStr = Field(..., description="Password for authentication")

    def authenticate(self) -> dict[str, str]:
        """
        Generate Basic authentication header.

        Returns:
            Dictionary with Authorization header containing Base64-encoded credentials

        Raises:
            HttpAuthenticationError: If the provided credentials are missing, invalid, or fail verification during the authentication process.
        """
        try:
            password_value = self.password.get_secret_value()

            # Combine username and password
            credentials = f"{self.username}:{password_value}"

            # Encode to Base64
            encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

            # Return Authorization header
            return {"Authorization": f"Basic {encoded}"}

        except Exception as e:
            raise HttpAuthenticationError(
                f"Failed to generate BasicAuthenticator header: {e}"
            )
