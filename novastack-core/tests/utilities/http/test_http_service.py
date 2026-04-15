from unittest.mock import Mock, patch

import httpx
import pytest
from novastack.core.utilities.http import HTTPService
from novastack.core.utilities.http.exceptions import (
    ConnectionError,
    RateLimitError,
    RequestTimeoutError,
)
from novastack.core.utilities.http.types import Response


class TestHTTPServiceCore:
    """Test core HTTPService functionality."""

    def test_init_without_auth(self):
        """Test initialization without authentication."""
        service = HTTPService(base_url="https://api.example.com")

        assert service.base_url == "https://api.example.com"
        assert service.timeout == 30.0
        assert service.verify_ssl is True
        assert service.auth_strategy is None

        service.close()

    def test_init_with_auth(self, basic_auth):
        """Test initialization with authentication."""
        service = HTTPService(
            base_url="https://api.example.com",
            auth_strategy=basic_auth,
        )

        assert service.auth_strategy is not None

        service.close()

    @patch("httpx.Client.get")
    def test_get_success(self, mock_get, http_service_no_auth, mock_httpx_response):
        """Test successful GET request."""
        mock_get.return_value = mock_httpx_response()

        response = http_service_no_auth.get("/users")

        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.is_success()

    @patch("httpx.Client.post")
    def test_post_with_json(self, mock_post, http_service_no_auth, mock_httpx_response):
        """Test POST request with JSON data."""
        mock_post.return_value = mock_httpx_response(status_code=201)

        json_data = {"name": "John"}
        response = http_service_no_auth.post("/users", json=json_data)

        assert response.status_code == 201

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_aget_success(
        self, mock_get, http_service_no_auth, mock_httpx_response
    ):
        """Test successful async GET request."""
        mock_get.return_value = mock_httpx_response()

        response = await http_service_no_auth.aget("/users")

        assert isinstance(response, Response)
        assert response.status_code == 200


class TestHTTPServiceErrorHandling:
    """Test critical error handling."""

    @patch("httpx.Client.get")
    def test_rate_limit_error(
        self, mock_get, http_service_no_auth, mock_httpx_response
    ):
        """Test rate limit error handling."""
        mock_get.return_value = mock_httpx_response(
            status_code=429, headers={"Retry-After": "60"}
        )

        with pytest.raises(RateLimitError) as exc_info:
            http_service_no_auth.get("/users")

        assert exc_info.value.status_code == 429

    @patch("httpx.Client.get")
    def test_timeout_error(self, mock_get, http_service_no_auth):
        """Test timeout error handling."""
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(RequestTimeoutError):
            http_service_no_auth.get("/users")

    @patch("httpx.Client.get")
    def test_connection_error(self, mock_get, http_service_no_auth):
        """Test connection error handling."""
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(ConnectionError):
            http_service_no_auth.get("/users")


class TestHTTPServiceAuthentication:
    """Test authentication integration."""

    @patch("httpx.Client.get")
    def test_basic_auth_headers(
        self, mock_get, http_service_basic_auth, mock_httpx_response
    ):
        """Test that basic auth headers are included."""
        mock_get.return_value = mock_httpx_response()

        http_service_basic_auth.get("/users")

        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    @patch("httpx.Client.get")
    def test_oauth_auth_headers(
        self,
        mock_get,
        http_service_oauth,
        mock_httpx_response,
        mock_oauth_token_response,
    ):
        """Test that OAuth headers are included."""
        with patch("httpx.Client.post") as mock_post:
            mock_token_response = Mock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = mock_oauth_token_response()
            mock_post.return_value = mock_token_response

            mock_get.return_value = mock_httpx_response()

            http_service_oauth.get("/users")

            call_args = mock_get.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")


class TestResponseWrapper:
    """Test Response wrapper critical methods."""

    def test_json_content(self):
        """Test JSON content parsing."""
        response = Response(
            status_code=200,
            headers={},
            content=b'{"name": "John"}',
            url="https://api.example.com/users/1",
        )

        json_data = response.json_content()
        assert json_data == {"name": "John"}

    def test_is_success(self):
        """Test is_success for success and error codes."""
        success_response = Response(
            status_code=200,
            headers={},
            content=b"",
            url="https://api.example.com/test",
        )
        assert success_response.is_success() is True

        error_response = Response(
            status_code=404,
            headers={},
            content=b"",
            url="https://api.example.com/test",
        )
        assert error_response.is_success() is False
