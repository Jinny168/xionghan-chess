from __future__ import annotations

from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


PROTOCOL_VERSION = 1


class MessageType(StrEnum):
    HELLO = "hello"
    JOIN = "join"
    STATE = "state"
    MOVE = "move"
    RESIGN = "resign"
    DRAW_OFFER = "draw_offer"
    DRAW_RESPONSE = "draw_response"
    UNDO_REQUEST = "undo_request"
    UNDO_RESPONSE = "undo_response"
    RESURRECT = "resurrect"
    RESTART = "restart"
    CHAT = "chat"
    PING = "ping"
    ERROR = "error"


class Envelope(BaseModel):
    type: MessageType
    request_id: str | None = Field(default=None, alias="requestId")
    room_id: str | None = Field(default=None, alias="roomId")
    revision: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    protocol_version: int = Field(default=PROTOCOL_VERSION, alias="protocolVersion")

    model_config = {"populate_by_name": True}

    def wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)
