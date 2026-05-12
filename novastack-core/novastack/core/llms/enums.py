from novastack.core.base.enum import BaseStrEnum


class MessageRole(BaseStrEnum):
    ASSISTANT = "assistant"
    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"
