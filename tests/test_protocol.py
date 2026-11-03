"""Synthetic offline protocol regression tests; no network access."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

spec = importlib.util.spec_from_file_location(
    "hoben_protocol", Path(__file__).parents[1] / "custom_components/hoben/protocol.py")
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)


def opened(product=5):
    data = bytearray(48)
    data[0], data[8], data[10], data[9] = 4, product, 8, 2
    data[14:46] = b"d" * 32
    data[46:48] = b"\x00\x02"
    return bytes(data)


def response(registers=None, transaction=65535, unit=1):
    registers = registers if registers is not None else [0] * 20
    return b"\x0e" + p.mbap(transaction, unit, b"\x04\x28" + struct.pack(">20H", *registers))


class ProtocolTests(unittest.TestCase):
    def test_guid_canonical(self):
        self.assertEqual(p.normalize_identifier("ABCDEF01-2345-6789-abcd-ef0123456789"),
                         "abcdef0123456789abcdef0123456789")

    def test_invalid_guids(self):
        for value in (None, True, "-" * 32, "g" * 32, "a" * 31, " a" * 32):
            with self.subTest(value=value), self.assertRaises(p.ProtocolError):
                p.normalize_identifier(value)

    def test_integer_validation(self):
        for value in (True, False, -1, 65536, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaises(p.ProtocolError):
                p.uint(value)

    def test_open_packet_vector(self):
        self.assertEqual(p.open_client("a" * 32, device_info="HA"),
                         b"\x03" + b"a" * 32 + b"\x00\x01\x22\x00" + b"0" * 32 + b"HA")

    def test_invalid_device_guid(self):
        for value in ("x" * 31, "é" * 32, None):
            with self.subTest(value=value), self.assertRaises(p.ProtocolError):
                p.open_client("a" * 32, value)

    def test_authorization_vector(self):
        self.assertEqual(p.authorization_response(0x1234), b"\x30\x34\x12")

    def test_opened_offsets(self):
        value = p.decode_opened_prefix(opened())
        self.assertEqual((value.product_type, value.software_major, value.software_minor,
                          value.application_version, value.profile), (5, 8, 2, 512, "v4"))
        self.assertNotIn("d" * 32, repr(value))

    def test_opened_suffix_rejected(self):
        for data in (opened()[:-1], opened() + b"\x0a", b"\x05" + opened()[1:]):
            with self.subTest(size=len(data)), self.assertRaises(p.ProtocolError):
                p.decode_opened_prefix(data)

    def test_unknown_profile_cannot_read(self):
        with self.assertRaises(p.UnsupportedProfile):
            p.read_v4_request(p.decode_opened_prefix(opened(3)))

    def test_read_vector(self):
        self.assertEqual(p.read_v4_request(p.decode_opened_prefix(opened())),
                         bytes.fromhex("0d ffff 0000 0006 01 04 0400 0014"))

    def test_read_response(self):
        self.assertEqual(p.decode_v4_response(response(list(range(20)))), tuple(range(20)))

    def test_transaction_and_unit_correlation(self):
        for data in (response(transaction=1), response(unit=2)):
            with self.assertRaises(p.ProtocolError):
                p.decode_v4_response(data)

    def test_bad_mbap(self):
        for prefix in (b"", bytes.fromhex("ffff00010006"),
                       bytes.fromhex("ffff00000001"), bytes.fromhex("ffff000000ff")):
            with self.assertRaises(p.ProtocolError):
                p.mbap_size(prefix)

    def test_frame_truncation_and_suffix(self):
        for data in (response()[:-1], response() + b"\x00"):
            with self.assertRaises(p.ProtocolError):
                p.decode_v4_response(data)

    def test_wrong_function(self):
        data = b"\x0e" + p.mbap(65535, 1, b"\x03\x28" + b"\x00" * 40)
        with self.assertRaises(p.ProtocolError):
            p.decode_v4_response(data)

    def test_modbus_exception(self):
        with self.assertRaisesRegex(p.ProtocolError, "^modbus_exception$"):
            p.decode_v4_response(b"\x0e" + p.mbap(65535, 1, b"\x84\x02"))

    def test_temperature(self):
        for raw, result in ((215, 21.5), (65526, -1.0), (0, 0.0), (4095, None)):
            self.assertEqual(p.temperature(raw), result)

    def test_known_state(self):
        r = [0] * 20
        r[0], r[4], r[6], r[7], r[8], r[11] = 0x0201, 2, 0x3205, 215, 220, 0x60
        state = p.decode_v4_state(tuple(r))
        self.assertEqual((state.ambient, state.target, state.power, state.on_off,
                          state.operation_mode, state.operation_state, state.ventilation),
                         (21.5, 22.0, 50, True, "manual", "combustion_management", "boost"))
        self.assertTrue(state.derogation_active and state.derogation_scheduled)
        self.assertNotIn("21.5", repr(state))

    def test_unknown_values_are_not_fallbacks(self):
        r = [0] * 20
        r[0], r[4], r[6] = 0xFEFE, 99, 0xFFFF
        state = p.decode_v4_state(tuple(r))
        self.assertIsNone(state.on_off)
        self.assertIsNone(state.power)
        self.assertIsNone(state.operation_mode)
        self.assertIsNone(state.operation_state)
        self.assertIsNone(state.ventilation)
        self.assertIsNone(state.target)

    def test_snapshot_shape(self):
        for registers in ((), [0] * 20, (0,) * 19, (True,) * 20, (-1,) * 20):
            with self.assertRaises(p.ProtocolError):
                p.decode_v4_state(registers)

    def test_every_fragment_boundary(self):
        data = b"\x0a" + response() + b"\x0a"
        for split in range(len(data) + 1):
            buffer = p.ResponseBuffer()
            events = buffer.feed(data[:split]) + buffer.feed(data[split:])
            self.assertEqual(events, [b"\x0a", response(), b"\x0a"])
            buffer.end_of_stream()

    def test_bytewise_fragmentation(self):
        buffer = p.ResponseBuffer()
        events = []
        for byte in response():
            events.extend(buffer.feed(bytes([byte])))
        self.assertEqual(events, [response()])

    def test_unknown_message_poisoning(self):
        buffer = p.ResponseBuffer()
        with self.assertRaises(p.ProtocolError):
            buffer.feed(b"\xff" + response())
        with self.assertRaisesRegex(p.ProtocolError, "^framer_failed$"):
            buffer.feed(response())

    def test_partial_eof(self):
        buffer = p.ResponseBuffer()
        buffer.feed(response()[:-1])
        with self.assertRaisesRegex(p.ProtocolError, "^truncated_message$"):
            buffer.end_of_stream()

    def test_buffer_cap(self):
        with self.assertRaises(p.ProtocolError):
            p.ResponseBuffer().feed(b"x" * 4097)

    def test_errors_do_not_echo_secrets(self):
        secret = "private-not-an-identifier"
        try:
            p.normalize_identifier(secret)
        except p.ProtocolError as exc:
            self.assertNotIn(secret, str(exc))


if __name__ == "__main__":
    unittest.main()
