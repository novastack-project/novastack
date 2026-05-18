from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseAuthenticator(BaseModel, ABC):
    """
    Abstract base class for authentication.

    All authentication strategies must implement the authenticate method
    to provide authentication headers for HTTP requests.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    @abstractmethod
    def authenticate(self) -> dict[str, str]:
        """Authenticate and return headers to be added to requests."""
