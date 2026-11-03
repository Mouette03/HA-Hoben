"""Read-only MyHOBEN protocol primitives; no sockets or Home Assistant imports.

Based on protocol research and codecs from Guillaume0385/ha-hoben-community
(MIT, Copyright (c) 2026 Guillaume0385). See LICENSE and docs/protocol-status.md.
The 48-byte OpenedClient prefix is NOT a proven complete message boundary.
"""
from dataclasses import dataclass, field
import re
import struct


class ProtocolError(ValueError):
    """Fixed public code; never include a packet, identifier or input value."""


class UnsupportedProfile(ProtocolError):
    pass


def uint(value: int, maximum: int = 65535) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ProtocolError("invalid_integer")
    return value


def normalize_identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
    ):
        raise ProtocolError("invalid_identifier_format")
    return value.replace("-", "").lower()


def device_identifier(value: str) -> bytes:
    if not isinstance(value, str) or len(value) != 32 or not value.isascii():
        raise ProtocolError("invalid_device_identifier")
    return value.encode("ascii")


def open_client(user_guid: str, device_guid: str = "0" * 32,
                device_info: str = "GitHubActions", build: int = 34) -> bytes:
    if not isinstance(device_info, str) or not 1 <= len(device_info) <= 256:
        raise ProtocolError("invalid_device_info")
    try:
        info = device_info.encode("utf-8")
    except UnicodeError:
        raise ProtocolError("invalid_device_info") from None
    return (b"\x03" + normalize_identifier(user_guid).encode("ascii") + b"\x00\x01"
            + uint(build).to_bytes(2, "little") + device_identifier(device_guid) + info)


def authorization_response(code: int) -> bytes:
    """Pure codec only. Caller must explicitly authorize any actual submission."""
    return b"\x30" + uint(code).to_bytes(2, "little")


@dataclass(frozen=True)
class OpenedPrefix:
    product_type: int
    revision: int
    software_major: int
    software_minor: int
    application_version: int
    device_guid: str = field(repr=False)

    @property
    def profile(self) -> str:
        return "v4" if self.product_type == 5 else "unsupported"


def decode_opened_prefix(data: bytes) -> OpenedPrefix:
    """Decode exactly the known prefix, never assert the full message size."""
    if not isinstance(data, bytes) or len(data) != 48 or data[0] != 4:
        raise ProtocolError("invalid_opened_prefix")
    try:
        device = data[14:46].decode("ascii")
    except UnicodeError:
        raise ProtocolError("invalid_opened_prefix") from None
    return OpenedPrefix(data[8], data[7], data[10], data[9],
                        int.from_bytes(data[46:48], "little"), device)


def read_v4_request(opened: OpenedPrefix) -> bytes:
    if not isinstance(opened, OpenedPrefix) or opened.profile != "v4":
        raise UnsupportedProfile("unsupported_profile")
    return b"\x0d" + mbap(65535, 1, struct.pack(">BHH", 4, 1024, 20))


def mbap(transaction: int, unit: int, pdu: bytes) -> bytes:
    if not isinstance(pdu, bytes) or not 1 <= len(pdu) <= 253:
        raise ProtocolError("invalid_pdu")
    return struct.pack(">HHHB", uint(transaction), 0, len(pdu) + 1, uint(unit, 255)) + pdu


def mbap_size(prefix: bytes) -> int:
    if not isinstance(prefix, bytes) or len(prefix) < 6:
        raise ProtocolError("invalid_mbap_prefix")
    _, protocol, length = struct.unpack_from(">HHH", prefix)
    if protocol != 0 or not 2 <= length <= 254:
        raise ProtocolError("invalid_mbap_header")
    return 6 + length


def decode_v4_response(data: bytes) -> tuple[int, ...]:
    if not isinstance(data, bytes) or len(data) < 9 or data[0] != 14:
        raise ProtocolError("invalid_data_response")
    frame = data[1:]
    if len(frame) != mbap_size(frame):
        raise ProtocolError("invalid_frame_length")
    transaction, _, _, unit = struct.unpack_from(">HHHB", frame)
    if transaction != 65535 or unit != 1:
        raise ProtocolError("uncorrelated_response")
    pdu = frame[7:]
    if pdu[0] == 0x84 and len(pdu) == 2:
        raise ProtocolError("modbus_exception")
    if len(pdu) != 42 or pdu[:2] != b"\x04\x28":
        raise ProtocolError("invalid_v4_response")
    return struct.unpack(">20H", pdu[2:])


def temperature(raw: int) -> float | None:
    uint(raw)
    if raw == 0x0FFF:
        return None
    return (raw - 65536 if raw & 0x8000 else raw) / 10


@dataclass(frozen=True, repr=False)
class V4State:
    """Household data: repr deliberately hides all measurements."""
    ambient: float | None
    target: float | None
    smoke: float | None
    combustion_air: float | None
    power: int | None
    on_off: bool | None
    operation_mode: str | None
    operation_state: str | None
    ventilation: str | None
    derogation_active: bool
    derogation_scheduled: bool


def decode_v4_state(registers: tuple[int, ...]) -> V4State:
    if not isinstance(registers, tuple) or len(registers) != 20:
        raise ProtocolError("invalid_snapshot")
    for value in registers:
        uint(value)
    target = temperature(registers[8])
    if target is not None and target < 5:
        target = None
    power = registers[6] >> 8
    return V4State(
        temperature(registers[7]), target, temperature(registers[17]),
        temperature(registers[16]), power if power <= 100 else None,
        {0: False, 1: True}.get(registers[0] & 255),
        {0: "automatic", 1: "magasin", 2: "manual"}.get(registers[0] >> 8),
        {0: "off", 1: "end_of_combustion", 2: "standard_start",
         3: "blackout_start", 4: "stabilization",
         5: "combustion_management"}.get(registers[6] & 255),
        {0: "normal", 1: "silence", 2: "boost"}.get(registers[4]),
        bool(registers[11] & 0x20), bool(registers[11] & 0x40),
    )


class ResponseBuffer:
    """Incremental post-open framing, not an OpenedClient boundary detector.

    Only Ping and DataResponseClient are accepted. Unknown messages abort;
    no byte scanning/resynchronization or interpretation of notifications.
    Returned events are bytes: Ping must be answered with Pong by the caller.
    """
    def __init__(self) -> None:
        self._buffer = bytearray()
        self._failed = False

    def feed(self, chunk: bytes) -> list[bytes]:
        if self._failed:
            raise ProtocolError("framer_failed")
        try:
            return self._feed(chunk)
        except ProtocolError:
            self._failed = True
            self._buffer.clear()
            raise

    def _feed(self, chunk: bytes) -> list[bytes]:
        if not isinstance(chunk, bytes) or len(self._buffer) + len(chunk) > 4096:
            raise ProtocolError("invalid_receive_chunk")
        self._buffer.extend(chunk)
        events = []
        while self._buffer:
            kind = self._buffer[0]
            if kind == 10:
                events.append(b"\x0a")
                del self._buffer[0]
            elif kind == 14:
                if len(self._buffer) < 7:
                    break
                size = 1 + mbap_size(bytes(self._buffer[1:7]))
                if len(self._buffer) < size:
                    break
                events.append(bytes(self._buffer[:size]))
                del self._buffer[:size]
            else:
                raise ProtocolError("unsupported_message")
        return events

    def end_of_stream(self) -> None:
        if self._buffer:
            self._failed = True
            self._buffer.clear()
            raise ProtocolError("truncated_message")
