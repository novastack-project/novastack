from typing import Any

import httpx
from novastack.core.bridge.pydantic import BaseModel, Field, PrivateAttr
from novastack.core.utilities.http.authenticators import NoAuthAuthenticator
from novastack.core.utilities.http.authenticators.base import BaseAuthenticator
from novastack.core.utilities.http.exceptions import (
    HttpConnectionError,
    HttpRequestError,
    HttpRequestTimeoutError,
)
from novastack.core.utilities.http.types import HttpResponse


class HttpService(BaseModel):
    """
    Enterprise-grade HTTP service with authentication and connection pooling.

    Provides both synchronous and asynchronous HTTP methods with pluggable
    authentication strategies.
    """

    model_config = {"arbitrary_types_allowed": True}

    base_url: str = Field(..., description="Base URL for all requests")
    timeout: float = Field(default=30.0, gt=0, description="Request timeout in seconds")
    verify_ssl: bool = Field(
        default=True, description="Whether to verify SSL certificates"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Default headers for all requests"
    )
    authenticator: BaseAuthenticator = Field(
        default_factory=NoAuthAuthenticator, description="Authentication strategy."
    )

    _client: httpx.Client = PrivateAttr()
    _async_client: httpx.AsyncClient = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:  # noqa: PYI063
        """Initialize HTTP clients after model creation."""
        # Initialize sync client
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers=self.headers,
        )

        # Initialize async client
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers=self.headers,
        )

    def _prepare_headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """
        Prepare request headers with authentication.

        Args:
            headers: Additional headers to include

        Returns:
            Combined headers with authentication
        """
        combined_headers = self.headers.copy()
        if headers:
            combined_headers.update(headers)

        # Apply authentication if strategy is provided
        if self.authenticator:
            auth_headers = self.authenticator.authenticate()
            combined_headers.update(auth_headers)

        return combined_headers

    def _handle_response(self, response: httpx.Response) -> HttpResponse:
        """
        Handle HTTP response and convert to HttpResponse object.

        Args:
            response: httpx response object

        Returns:
            HttpResponse object

        Raises:
            HttpRequestError: For other HTTP errors
        """
        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            url=str(response.url),
        )

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform synchronous GET request.

        Args:
            url: Request url
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.get(url, params=params, headers=prepared_headers)
            return self._handle_response(response)

        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"GET request failed: {e}")

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform synchronous POST request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.post(
                url, data=data, json=json, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"POST request failed: {e}")

    def put(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform synchronous PUT request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.put(
                url, data=data, json=json, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"PUT request failed: {e}")

    def delete(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform synchronous DELETE request.

        Args:
            url: Request url (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.delete(url, params=params, headers=prepared_headers)
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"DELETE request failed: {e}")

    async def aget(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform asynchronous GET request.

        Args:
            url: Request url (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.get(
                url, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"GET request failed: {e}")

    async def apost(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform asynchronous POST request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.post(
                url, data=data, json=json, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"POST request failed: {e}")

    async def aput(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform asynchronous PUT request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.put(
                url, data=data, json=json, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"PUT request failed: {e}")

    async def adelete(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """
        Perform asynchronous DELETE request.

        Args:
            url: Request url (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            HttpResponse object

        Raises:
            HttpConnectionError: If connection fails
            HttpRequestTimeoutError: If request times out
            HttpRequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.delete(
                url, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise HttpRequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise HttpConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise HttpRequestError(f"DELETE request failed: {e}")

    def close(self) -> None:
        if self._client:
            self._client.close()

    async def aclose(self) -> None:
        if self._async_client:
            await self._async_client.aclose()
