import base64
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from novastack.core.bridge.pydantic import SecretStr
from novastack.core.utilities.http.authenticators import (
    BasicAuthenticator,
    NoAuthAuthenticator,
    OAuth2Authenticator,
    OAuth2GrantType,
)
from novastack.core.utilities.http.exceptions import AuthenticationError


class TestBasicAuthStrategy:
    """Test BasicAuthenticator critical functionality."""

    def test_initialization(self):
        """Test BasicAuthenticator initialization."""
        auth = BasicAuthenticator(username="testuser", password=SecretStr("testpass"))

        assert auth.username == "testuser"
        assert auth.password.get_secret_value() == "testpass"

    def test_authenticate_encoding(self, basic_auth):
        """Test successful authentication with proper Base64 encoding."""
        headers = basic_auth.authenticate()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

        # Verify Base64 encoding
        encoded_part = headers["Authorization"].split(" ")[1]
        decoded = base64.b64decode(encoded_part).decode("utf-8")
        assert decoded == "testuser:testpass"

    def test_empty_username_validation(self):
        """Test validation fails with empty username."""
        with pytest.raises(ValueError):
            BasicAuthenticator(username="", password=SecretStr("testpass"))


class TestOAuthStrategy:
    """Test OAuth2Authenticator critical functionality."""

    def test_initialization(self, oauth_client_credentials):
        """Test OAuth2Authenticator initialization."""
        from novastack.core.utilities.http.authenticators.oauth2_authenticator import (
            OAuth2GrantType,
        )

        assert oauth_client_credentials.token_url == "https://auth.example.com/token"
        assert oauth_client_credentials.client_id == "test_client_id"
        assert oauth_client_credentials.grant_type == OAuth2GrantType.CLIENT_CREDENTIALS

    @patch("httpx.post")
    def test_token_acquisition(
        self, mock_post, oauth_client_credentials, mock_oauth_token_response
    ):
        """Test successful token acquisition."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_oauth_token_response()
        mock_post.return_value = mock_response

        headers = oauth_client_credentials.authenticate()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_access_token"

    @patch("httpx.post")
    def test_token_caching(
        self, mock_post, oauth_client_credentials, mock_oauth_token_response
    ):
        """Test that token is cached and reused."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_oauth_token_response()
        mock_post.return_value = mock_response

        # First call should acquire token
        headers1 = oauth_client_credentials.authenticate()

        # Second call should reuse cached token
        headers2 = oauth_client_credentials.authenticate()

        assert headers1 == headers2
        # Token endpoint should only be called once
        assert mock_post.call_count == 1

    @patch("httpx.post")
    def test_token_expiry_detection(
        self, mock_post, oauth_client_credentials, mock_oauth_token_response
    ):
        """Test token expiry detection with buffer."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_oauth_token_response(expires_in=3600)
        mock_post.return_value = mock_response

        # Get initial token
        oauth_client_credentials.authenticate()

        # Token should not be expired
        assert oauth_client_credentials.is_expired() is False

        # Manually set expiration to past
        oauth_client_credentials._expires_at = datetime.now() - timedelta(hours=1)

        # Token should now be expired
        assert oauth_client_credentials.is_expired() is True

    @patch("httpx.post")
    def test_automatic_token_refresh(
        self, mock_post, oauth_client_credentials, mock_oauth_token_response
    ):
        """Test automatic token refresh when expired."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_oauth_token_response()
        mock_post.return_value = mock_response

        # Get initial token
        oauth_client_credentials.authenticate()

        # Manually expire the token
        oauth_client_credentials._expires_at = datetime.now() - timedelta(hours=1)

        # Next authenticate should refresh token
        headers = oauth_client_credentials.authenticate()

        assert "Authorization" in headers
        # Should have called token endpoint twice (initial + refresh)
        assert mock_post.call_count == 2

    @patch("httpx.post")
    def test_failed_token_request(self, mock_post, oauth_client_credentials):
        """Test handling of failed token request."""
        import httpx

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        # Mock raise_for_status to raise HTTPStatusError
        def raise_for_status():
            raise httpx.HTTPStatusError(
                "401 Unauthorized", request=Mock(), response=mock_response
            )

        mock_response.raise_for_status = raise_for_status
        mock_post.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            oauth_client_credentials.authenticate()

        assert "401" in str(exc_info.value)

    @patch("httpx.post")
    def test_expiry_buffer_enforcement(
        self, mock_post, oauth_client_credentials, mock_oauth_token_response
    ):
        """Test that 60-second expiry buffer is enforced."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_oauth_token_response()
        mock_post.return_value = mock_response

        oauth_client_credentials.authenticate()

        # Set expiration to 30 seconds from now (within buffer)
        oauth_client_credentials._expires_at = datetime.now() + timedelta(seconds=30)

        # Should be considered expired due to 60-second buffer
        assert oauth_client_credentials.is_expired() is True

    def test_grant_type_accepts_string(self):
        """Test that grant_type accepts string values."""
        # Test with string
        auth_string = OAuth2Authenticator(
            token_url="https://auth.example.com/token",
            client_id="test_client",
            client_secret=SecretStr("test_secret"),
            grant_type="password",
            username="testuser",
            password=SecretStr("testpass"),
        )

        assert auth_string.grant_type == OAuth2GrantType.PASSWORD

        # Test with enum
        auth_enum = OAuth2Authenticator(
            token_url="https://auth.example.com/token",
            client_id="test_client",
            client_secret=SecretStr("test_secret"),
            grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
        )

        assert auth_enum.grant_type == OAuth2GrantType.CLIENT_CREDENTIALS

    def test_grant_type_invalid_string(self):
        """Test that invalid grant_type string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            OAuth2Authenticator(
                token_url="https://auth.example.com/token",
                client_id="test_client",
                client_secret=SecretStr("test_secret"),
                grant_type="invalid_grant_type",
            )

        assert "Invalid value for parameter 'grant_type'" in str(exc_info.value)
        assert "invalid_grant_type" in str(exc_info.value)

    def test_grant_type_invalid_type(self):
        """Test that invalid grant_type type (not string or enum) raises TypeError."""
        # Test with int
        with pytest.raises(TypeError) as exc_info:
            OAuth2Authenticator(
                token_url="https://auth.example.com/token",
                client_id="test_client",
                client_secret=SecretStr("test_secret"),
                grant_type=123,  # type: ignore
            )

        assert "Invalid type for parameter 'grant_type'" in str(exc_info.value)
        assert "int" in str(exc_info.value)

        # Test with list
        with pytest.raises(TypeError) as exc_info:
            OAuth2Authenticator(
                token_url="https://auth.example.com/token",
                client_id="test_client",
                client_secret=SecretStr("test_secret"),
                grant_type=["password"],  # type: ignore
            )

        assert "Invalid type for parameter 'grant_type'" in str(exc_info.value)
        assert "list" in str(exc_info.value)


class TestNoAuthStrategy:
    """Test NoAuthAuthenticator - default for open APIs."""

    def test_no_auth_returns_empty_headers(self):
        """Test that NoAuth returns empty authentication headers."""
        auth = NoAuthAuthenticator()
        headers = auth.authenticate()

        assert headers == {}
        assert isinstance(headers, dict)
