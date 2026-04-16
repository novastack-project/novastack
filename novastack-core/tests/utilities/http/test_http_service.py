from unittest.mock import Mock, patch

import httpx
import pytest
from novastack.core.utilities.http import HttpService
from novastack.core.utilities.http.exceptions import (
    HttpConnectionError,
    HttpRequestTimeoutError,
)
from novastack.core.utilities.http.types import HttpResponse


class TestHttpServiceCore:

    def test_init_without_auth(self):
        service = HttpService(base_url="https://api.example.com")

        assert service.base_url == "https://api.example.com"
        assert service.timeout == 30.0
        assert service.verify_ssl is True
        assert service.authenticator is not None

        service.close()

    def test_init_with_auth(self, basic_auth):
        service = HttpService(
            base_url="https://api.example.com",
            authenticator=basic_auth,
        )

        assert service.authenticator is not None

        service.close()

    @patch("httpx.Client.get")
    def test_get_success(self, mock_get, http_service_no_auth, mock_httpx_response):
        mock_get.return_value = mock_httpx_response()

        response = http_service_no_auth.get("/users")

        assert isinstance(response, HttpResponse)
        assert response.status_code == 200
        assert response.is_success()

    @patch("httpx.Client.post")
    def test_post_with_json(self, mock_post, http_service_no_auth, mock_httpx_response):
        mock_post.return_value = mock_httpx_response(status_code=201)

        json_data = {"name": "John"}
        response = http_service_no_auth.post("/users", json=json_data)

        assert response.status_code == 201

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_aget_success(
        self, mock_get, http_service_no_auth, mock_httpx_response
    ):
        mock_get.return_value = mock_httpx_response()

        response = await http_service_no_auth.aget("/users")

        assert isinstance(response, HttpResponse)
        assert response.status_code == 200


class TestHttpServiceErrorHandling:

    @patch("httpx.Client.get")
    def test_timeout_error(self, mock_get, http_service_no_auth):
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(HttpRequestTimeoutError):
            http_service_no_auth.get("/users")

    @patch("httpx.Client.get")
    def test_connection_error(self, mock_get, http_service_no_auth):
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(HttpConnectionError):
            http_service_no_auth.get("/users")


class TestHttpServiceAuthentication:

    @patch("httpx.Client.get")
    def test_basic_auth_headers(
        self, mock_get, http_service_basic_auth, mock_httpx_response
    ):
        mock_get.return_value = mock_httpx_response()

        http_service_basic_auth.get("/users")

        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    @patch("httpx.post")
    @patch("httpx.Client.get")
    def test_oauth_auth_headers(
        self,
        mock_get,
        mock_httpx_post,
        http_service_oauth,
        mock_httpx_response,
        mock_oauth_token_response,
    ):
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = mock_oauth_token_response()
        mock_token_response.raise_for_status = Mock()
        mock_httpx_post.return_value = mock_token_response

        mock_get.return_value = mock_httpx_response()

        http_service_oauth.get("/users")

        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")


class TestHttpResponseWrapper:

    def test_json_content(self):
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b'{"name": "John"}',
            url="https://api.example.com/users/1",
        )

        json_data = response.json_content()
        assert json_data == {"name": "John"}

    def test_is_success(self):
        success_response = HttpResponse(
            status_code=200,
            headers={},
            content=b"",
            url="https://api.example.com/test",
        )
        assert success_response.is_success() is True

        error_response = HttpResponse(
            status_code=404,
            headers={},
            content=b"",
            url="https://api.example.com/test",
        )
        assert error_response.is_success() is False
