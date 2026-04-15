from typing import TYPE_CHECKING, Any

import httpx
from novastack.core.bridge.pydantic import BaseModel, Field, PrivateAttr
from novastack.core.utilities.http.authenticators import NoAuthAuthenticator
from novastack.core.utilities.http.exceptions import (
    ConnectionError,
    RequestError,
    RequestTimeoutError,
)
from novastack.core.utilities.http.types import HTTPResponse

if TYPE_CHECKING:
    from novastack.core.utilities.http.authenticators.base import BaseAuthenticator


class HTTPService(BaseModel):
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
    authenticator: "BaseAuthenticator" = Field(
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

    def _handle_response(self, response: httpx.Response) -> HTTPResponse:
        """
        Handle HTTP response and convert to HTTPResponse object.

        Args:
            response: httpx response object

        Returns:
            HTTPResponse object

        Raises:
            RequestError: For other HTTP errors
        """
        return HTTPResponse(
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
    ) -> HTTPResponse:
        """
        Perform synchronous GET request.

        Args:
            url: Request url
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.get(url, params=params, headers=prepared_headers)
            return self._handle_response(response)

        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"GET request failed: {e}")

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """
        Perform synchronous POST request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.post(
                url, data=data, json=json, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"POST request failed: {e}")

    def put(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """
        Perform synchronous PUT request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.put(
                url, data=data, json=json, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"PUT request failed: {e}")

    def delete(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """
        Perform synchronous DELETE request.

        Args:
            url: Request url (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = self._client.delete(url, params=params, headers=prepared_headers)
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"DELETE request failed: {e}")

    async def aget(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """
        Perform asynchronous GET request.

        Args:
            url: Request url (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.get(
                url, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"GET request failed: {e}")

    async def apost(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """
        Perform asynchronous POST request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.post(
                url, data=data, json=json, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"POST request failed: {e}")

    async def aput(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """
        Perform asynchronous PUT request.

        Args:
            url: Request url (relative to base_url)
            data: Form data
            json: JSON data
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.put(
                url, data=data, json=json, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"PUT request failed: {e}")

    async def adelete(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """
        Perform asynchronous DELETE request.

        Args:
            url: Request url (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTPResponse object

        Raises:
            ConnectionError: If connection fails
            RequestTimeoutError: If request times out
            RequestError: For other errors
        """
        try:
            prepared_headers = self._prepare_headers(headers)
            response = await self._async_client.delete(
                url, params=params, headers=prepared_headers
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(str(e))
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise RequestError(f"DELETE request failed: {e}")

    def close(self) -> None:
        if self._client:
            self._client.close()

    async def aclose(self) -> None:
        if self._async_client:
            await self._async_client.aclose()
