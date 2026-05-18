from novastack.common.enums import BaseStrEnum


class MessageRole(BaseStrEnum):
    ASSISTANT = "assistant"
    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"
