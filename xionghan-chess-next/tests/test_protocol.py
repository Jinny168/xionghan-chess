import pytest
from pydantic import ValidationError

from xionghan_chess.core.protocol import Envelope, MessageType, PROTOCOL_VERSION


def test_protocol_uses_stable_camel_case_wire_format():
    message = Envelope(type=MessageType.MOVE, requestId="abc", roomId="R12345", revision=3,
                       payload={"from": {"row": 1, "col": 2}, "to": {"row": 2, "col": 2}})
    wire = message.wire()
    assert wire["requestId"] == "abc"
    assert wire["roomId"] == "R12345"
    assert wire["protocolVersion"] == PROTOCOL_VERSION


def test_pause_message_is_part_of_the_shared_protocol():
    message = Envelope(type=MessageType.PAUSE, payload={"paused": True})
    assert message.wire()["type"] == "pause"


def test_unsupported_protocol_version_is_rejected():
    with pytest.raises(ValidationError):
        Envelope.model_validate({"type": "ping", "protocolVersion": PROTOCOL_VERSION + 1})
