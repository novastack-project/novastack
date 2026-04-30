from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Union

import httpx
from novastack.core.bridge.pydantic import (
    Field,
    PrivateAttr,
    SecretStr,
    field_validator,
)
from novastack.core.utilities.http.authenticators.base import BaseAuthenticator
from novastack.core.utilities.http.exceptions import HttpAuthenticationError


class OAuth2GrantType(str, Enum):
    """
    Supported OAuth2 grant type.

    Attributes:
        CLIENT_CREDENTIALS (str): "client_credentials"
        PASSWORD (str):"password"
        AUTHORIZATION_CODE (str): "authorization_code"
        REFRESH_TOKEN (str): "refresh_token"
    """

    CLIENT_CREDENTIALS = "client_credentials"
    PASSWORD = "password"
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"


class OAuth2Authenticator(BaseAuthenticator):
    """
    OAuth 2.0 authentication.

    Automatically manages token lifecycle including expiration tracking and refresh.
    """

    token_url: str = Field(..., description="OAuth2 token endpoint URL")
    client_id: str = Field(..., min_length=1, description="OAuth2 client ID")
    client_secret: SecretStr = Field(..., description="OAuth2 client secret")
    grant_type: OAuth2GrantType = Field(
        default=OAuth2GrantType.CLIENT_CREDENTIALS, description="OAuth2 grant type"
    )
    username: str | None = Field(
        default=None, description="Username for password grant_type"
    )
    password: SecretStr | None = Field(
        default=None, description="Password for password grant_type"
    )
    scope: str | None = Field(
        default=None, description="Optional OAuth scope to request"
    )

    _access_token: str | None = PrivateAttr(default=None)
    _token_type: str = PrivateAttr(default="Bearer")
    _expires_at: datetime | None = PrivateAttr(default=None)
    _refresh_token: str | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:  # noqa: PYI063
        if self.grant_type == OAuth2GrantType.PASSWORD:
            if not self.username or not self.password:
                raise HttpAuthenticationError(
                    "'username' and 'password' are required for PASSWORD grant_type."
                )

    def authenticate(self) -> dict[str, str]:
        """
        Get authentication headers with valid access token.

        Automatically refreshes token if expired.

        Returns:
            Dictionary with Authorization header containing access token

        Raises:
            HttpAuthenticationError: If the provided credentials are missing, invalid, or fail verification during the authentication process.
        """
        # Check if token needs refresh
        if self.is_expired():
            self.refresh_token()

        # If still no token, get a new one
        if not self._access_token:
            self._get_access_token()

        return {"Authorization": f"{self._token_type} {self._access_token}"}

    def refresh_token(self) -> None:
        """
        Refresh OAuth2 token.

        Attempts to use refresh token if available, otherwise obtains new token.

        Raises:
            HttpAuthenticationError: If the provided credentials are missing, invalid, or fail verification during the authentication process.
        """
        # If we have a refresh token, try to use it
        if self._refresh_token:
            try:
                self._get_access_token(use_refresh_token=True)
                return
            except HttpAuthenticationError:
                # If refresh fails, fall through to get new token
                pass

        self._get_access_token()

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

    def _get_access_token(self, use_refresh_token: bool = False) -> None:
        """
        Get OAuth2 access token from token endpoint.

        Args:
            use_refresh_token: Whether to use refresh token grant

        Raises:
            HttpAuthenticationError: If the provided credentials are missing, invalid, or fail verification during the authentication process.
        """
        try:
            # Build request payload
            data = self._build_token_request_data(use_refresh_token)

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
                    "No 'access_token' in authenticator response"
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
                f"Token request failed with status {e.response.status_code}: {error_detail}"
            )
        except httpx.TimeoutException as e:
            raise HttpAuthenticationError(f"Token request timed out: {e}")
        except httpx.ConnectError as e:
            raise HttpAuthenticationError(f"Failed to connect to token endpoint: {e}")
        except HttpAuthenticationError:
            raise
        except Exception as e:
            raise HttpAuthenticationError(f"Failed to get OAuth2 token: {e}")

    def _build_token_request_data(self, use_refresh_token: bool) -> dict[str, str]:
        """
        Build OAuth2 token request payload.

        Args:
            use_refresh_token: Whether to use refresh token grant

        Returns:
            Dictionary containing the token request data
        """
        base_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret.get_secret_value(),
        }

        if use_refresh_token and self._refresh_token:
            data = {
                "grant_type": OAuth2GrantType.REFRESH_TOKEN.value,
                "refresh_token": self._refresh_token,
                **base_data,
            }
        elif self.grant_type == OAuth2GrantType.PASSWORD:
            data = {
                "grant_type": self.grant_type.value,
                "username": self.username,
                "password": self.password.get_secret_value() if self.password else None,
                **base_data,
            }
        else:
            data = {
                "grant_type": self.grant_type.value,
                **base_data,
            }

        # Add optional scope
        if self.scope:
            data["scope"] = self.scope

        return data
