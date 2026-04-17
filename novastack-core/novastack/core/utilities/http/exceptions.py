class HttpRequestError(Exception):
    """Generic exception for HTTP service errors."""


class HttpAuthenticationError(Exception):
    """Raised when authentication fails."""


class HttpRequestTimeoutError(HttpRequestError):
    """Raised when a request times out."""


class HttpConnectionError(HttpRequestError):
    """Raised when connection to server fails."""
