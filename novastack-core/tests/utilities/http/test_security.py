import base64
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from novastack.core.utilities.http import HttpService
from novastack.core.utilities.http.authenticators import (
    BasicAuthenticator,
    OAuth2Authenticator,
    OAuth2GrantType,
)
from novastack.core.utilities.http.exceptions import HttpAuthenticationError


class TestCredentialMasking:
    def test_basic_auth_password_masked(self):
        auth = BasicAuthenticator(username="testuser", password="supersecret")

        auth_str = str(auth)
        auth_repr = repr(auth)

        # Password should not appear in plain text
        assert "supersecret" not in auth_str
        assert "supersecret" not in auth_repr

    def test_oauth_client_secret_masked(self):
        oauth = OAuth2Authenticator(
            token_url="https://auth.example.com/token",
            client_id="test_client",
            client_secret="supersecret",
            grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
        )

        oauth_str = str(oauth)
        oauth_repr = repr(oauth)

        # Secret should not appear in plain text
        assert "supersecret" not in oauth_str
        assert "supersecret" not in oauth_repr

    @patch("httpx.Client.post")
    def test_credentials_not_in_error_messages(self, mock_post):
        oauth = OAuth2Authenticator(
            token_url="https://auth.example.com/token",
            client_id="test_client",
            client_secret="supersecret",
            grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
        )

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_post.return_value = mock_response

        try:
            oauth.authenticate()
        except HttpAuthenticationError as e:
            error_msg = str(e)
            assert "supersecret" not in error_msg


class TestSSLVerification:
    def test_ssl_verification_enabled_by_default(self):
        service = HttpService(base_url="https://api.example.com")

        assert service.verify_ssl is True

        service.close()

    def test_ssl_verification_can_be_disabled(self):
        service = HttpService(
            base_url="https://api.example.com",
            verify_ssl=False,
        )

        assert service.verify_ssl is False

        service.close()


class TestTokenExpiryEnforcement:
    @patch("httpx.post")
    @patch("httpx.Client.get")
    def test_expired_token_not_used(self, mock_get, mock_httpx_post):
        oauth = OAuth2Authenticator(
            token_url="https://auth.example.com/token",
            client_id="test_client",
            client_secret="test_secret",
            grant_type=OAuth2GrantType.CLIENT_CREDENTIALS,
        )

        service = HttpService(
            base_url="https://api.example.com",
            authenticator=oauth,
        )

        # Mock initial token response
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "initial_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_token_response.raise_for_status = Mock()
        mock_httpx_post.return_value = mock_token_response

        # Mock API response
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.content = b'{"data": "test"}'
        mock_api_response.headers = {}
        mock_api_response.url = "https://api.example.com/test"
        mock_get.return_value = mock_api_response

        # First request
        service.get("/test")
        initial_token_calls = mock_httpx_post.call_count

        # Manually expire the token
        oauth._expires_at = datetime.now() - timedelta(hours=1)

        # Mock new token response
        mock_token_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        # Second request should get new token
        service.get("/test")

        assert mock_httpx_post.call_count > initial_token_calls

        service.close()
