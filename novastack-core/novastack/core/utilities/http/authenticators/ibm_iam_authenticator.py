from datetime import datetime, timedelta

import httpx
from novastack.core.bridge.pydantic import Field, PrivateAttr, SecretStr
from novastack.core.utilities.http.authenticators.base import BaseAuthenticator
from novastack.core.utilities.http.exceptions import HttpAuthenticationError


class IBMIAMAuthenticator(BaseAuthenticator):
    """
    IBM Cloud IAM authentication.

    Uses IBM Cloud API Key to obtain access tokens from IBM IAM service.
    Automatically manages token lifecycle including expiration tracking and refresh.
    """

    api_key: SecretStr = Field(..., description="IBM Cloud API Key")
    token_url: str = Field(
        default="https://iam.cloud.ibm.com/identity/token",
        description="IBM IAM token endpoint URL",
    )

    _access_token: str | None = PrivateAttr(default=None)
    _token_type: str = PrivateAttr(default="Bearer")
    _expires_at: datetime | None = PrivateAttr(default=None)
    _refresh_token: str | None = PrivateAttr(default=None)

    def authenticate(self) -> dict[str, str]:
        """
        Get authentication headers with valid access token.

        Automatically refreshes token if expired.

        Returns:
            Dictionary with Authorization header containing access token

        Raises:
            HttpAuthenticationError: If token acquisition fails
        """
        # Check if token needs refresh
        if self.is_expired():
            self._get_access_token()

        return {"Authorization": f"{self._token_type} {self._access_token}"}

    def is_expired(self) -> bool:
        """
        Check if access token is expired.

        Returns:
            True if token is expired or will expire within 60 seconds, False otherwise
        """
        if not self._access_token or not self._expires_at:
            return True

        # Consider token expired if it expires within 60 seconds
        buffer = timedelta(seconds=60)
        return datetime.now() >= (self._expires_at - buffer)

    def _get_access_token(self) -> None:
        """
        Get IBM IAM access token.

        Raises:
            HttpAuthenticationError: If token acquisition fails
        """
        try:
            data = {
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self.api_key.get_secret_value(),
            }

            # Make token request
            response = httpx.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Raise for any HTTP error status
            response.raise_for_status()

            token_data = response.json()

            self._access_token = token_data.get("access_token")
            if not self._access_token:
                raise HttpAuthenticationError(
                    "No 'access_token' in IBM IAM token response"
                )

            self._token_type = token_data.get("token_type", "Bearer")
            self._refresh_token = token_data.get("refresh_token")

            # Calculate expiration time
            expires_in = token_data.get("expires_in")
            if expires_in:
                self._expires_at = datetime.now() + timedelta(seconds=int(expires_in))
            else:
                # Default to 1 hour if not provided
                self._expires_at = datetime.now() + timedelta(hours=1)

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            raise HttpAuthenticationError(
                f"IBM IAM token request failed with status {e.response.status_code}: {error_detail}"
            )
        except httpx.TimeoutException as e:
            raise HttpAuthenticationError(f"IBM IAM token request timed out: {e}")
        except httpx.ConnectError as e:
            raise HttpAuthenticationError(f"Failed to connect to IBM IAM endpoint: {e}")
        except HttpAuthenticationError:
            raise
        except Exception as e:
            raise HttpAuthenticationError(f"Failed to obtain IBM IAM token: {e}")
