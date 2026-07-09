from typing import Any, Literal

from donkey.core.bridge.pydantic import BaseModel, SecretStr


class IntegratedSystemCredentials(BaseModel):
    """
    Encapsulates the credentials for an Integrated System based on the authentication type.

    Depending on the `auth_type`, only a subset of the properties is required.

    Attributes:
        auth_type (str): The type of authentication. Currently supports "basic" and "bearer".
        username (str, optional): The username for Basic Authentication.
        password (str, optional): The password for Basic Authentication.
        token_url (str, optional): The URL of the authentication endpoint used to request a Bearer token.
        token_method (str, optional): The HTTP method (e.g., "POST", "GET") used to request the Bearer token.
            Defaults to "POST".
        token_headers (dict, optional): Optional headers to include when requesting the Bearer token.
            Defaults to `None`.
        token_payload (str | dict, optional): The body or payload to send when requesting the Bearer token.
            Can be a string (e.g., raw JSON). Defaults to `None`.
    """

    auth_type: Literal["basic", "bearer"]
    username: str | None = None  # basic
    password: SecretStr | None = None  # basic
    token_url: str | None = None  # bearer
    token_method: str | None = "POST"  # bearer
    token_headers: dict | None = {}  # bearer
    token_payload: str | dict | None = None  # bearer

    def model_post_init(self, __context: Any) -> None:  # noqa: PYI063
        if self.auth_type == "basic":
            if not self.username or not self.password:
                raise ValueError(
                    "`username` and `password` are required for auth_type = 'basic'.",
                )
        elif self.auth_type == "bearer":
            if not self.token_url:
                raise ValueError(
                    "`token_url` are required for auth_type = 'bearer'.",
                )

    def to_dict(self) -> dict:
        integrated_system_creds = {"auth_type": self.auth_type}

        if self.auth_type == "basic":
            integrated_system_creds["username"] = self.username
            integrated_system_creds["password"] = self.password.get_secret_value()
        elif self.auth_type == "bearer":
            integrated_system_creds["token_info"] = {
                "url": self.token_url,
                "method": self.token_method,
                "headers": self.token_headers,
                "payload": self.token_payload,
            }

        return integrated_system_creds
