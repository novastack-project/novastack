import pytest
from novastack.core.bridge.pydantic import SecretStr
from novastack.core.utilities.http.authenticators import (
    BasicAuthenticator,
    OAuth2Authenticator,
)
from novastack.core.utilities.http.authenticators.oauth2_authenticator import (
    OAuth2GrantType,
)


@pytest.fixture
def basic_auth():
    """Fixture for BasicAuthenticator instance."""
    return BasicAuthenticator(username="testuser", password=SecretStr("testpass"))


@pytest.fixture
def oauth_client_credentials():
    """Fixture for OAuth2Authenticator with client_credentials grant."""
    return OAuth2Authenticator(
        token_url="https://auth.example.com/token",
        client_id="test_client_id",
        client_secret=SecretStr("test_client_secret"),
        grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
    )


@pytest.fixture
def oauth_password_grant():
    """Fixture for OAuth2Authenticator with password grant."""
    return OAuth2Authenticator(
        token_url="https://auth.example.com/token",
        client_id="test_client_id",
        client_secret=SecretStr("test_client_secret"),
        grant_type=OAuth2GrantType.PASSWORD,
        username="testuser",
        password=SecretStr("testpass"),
    )


@pytest.fixture
def mock_oauth_token_response():
    """Fixture for mock OAuth2 token response."""

    def _response(
        access_token: str = "test_access_token",
        token_type: str = "Bearer",
        expires_in: int = 3600,
        refresh_token: str | None = None,
    ):
        response = {
            "access_token": access_token,
            "token_type": token_type,
            "expires_in": expires_in,
        }
        if refresh_token:
            response["refresh_token"] = refresh_token
        return response

    return _response
