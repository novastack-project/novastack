class RequestError(Exception):
    """Generic exception for HTTP service errors."""


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class RequestTimeoutError(RequestError):
    """Raised when a request times out."""


class ConnectionError(RequestError):
    """Raised when connection to server fails."""
