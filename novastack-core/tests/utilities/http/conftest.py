import pytest
from novastack.core.bridge.pydantic import SecretStr
from novastack.core.utilities.http import HttpService
from novastack.core.utilities.http.authenticators import (
    BasicAuthenticator,
    OAuth2Authenticator,
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


@pytest.fixture
def mock_httpx_response():
    """Fixture for mock httpx response."""
    from unittest.mock import Mock

    def _response(status_code=200, content=b'{"data": "test"}', headers=None):
        response = Mock()
        response.status_code = status_code
        response.content = content
        response.headers = headers or {}
        response.url = "https://api.example.com/test"
        return response

    return _response


@pytest.fixture
def http_service_no_auth():
    """Fixture for HttpService without authentication."""
    service = HttpService(base_url="https://api.example.com")
    yield service
    service.close()


@pytest.fixture
def http_service_basic_auth(basic_auth):
    """Fixture for HttpService with basic authentication."""
    service = HttpService(
        base_url="https://api.example.com",
        authenticator=basic_auth,
    )
    yield service
    service.close()


@pytest.fixture
def http_service_oauth(oauth_client_credentials):
    """Fixture for HttpService with OAuth authentication."""
    service = HttpService(
        base_url="https://api.example.com",
        authenticator=oauth_client_credentials,
    )
    yield service
    service.close()
