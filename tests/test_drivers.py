import time
import socket
import threading
import pytest

from arinc429.drivers import (
    ArincFrameParser,
    SerialTransport,
    SocketTransport,
    BaseArincDriver,
)
from arinc429.word import Word
from arinc429.sim import ArincBus


class FakeBus(ArincBus):
    def __init__(self):
        super().__init__()
        self._events = []

    def publish(self, channel, payload):
        self._events.append((channel, payload))

    @property
    def events(self):
        return list(self._events)


class FakeTransport:
    def __init__(self, incoming_chunks=None):
        self.incoming_chunks = list(incoming_chunks or [])
        self.outgoing = []
        self.opened = False
        self.closed = False

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def read(self, max_bytes: int) -> bytes:
        if not self.incoming_chunks:
            return b""
        return self.incoming_chunks.pop(0)

    def write(self, payload: bytes) -> None:
        self.outgoing.append(payload)


class DummyDriver(BaseArincDriver):
    def __init__(self, bus, transport, parser=None):
        super().__init__(bus, transport, parser)


def test_parser_single_word():
    parser = ArincFrameParser()
    data = (123).to_bytes(4, "big")
    words = parser.parse(data)
    assert len(words) == 1
    assert isinstance(words[0], Word)
    assert words[0].raw == 123


def test_parser_multiple_words():
    parser = ArincFrameParser()
    data = (1).to_bytes(4, "big") + (2).to_bytes(4, "big")
    words = parser.parse(data)
    assert [w.raw for w in words] == [1, 2]


def test_parser_fragmented_input():
    parser = ArincFrameParser()
    words = parser.parse(b"\x00\x00")
    assert words == []
    words = parser.parse(b"\x00\x01")
    assert len(words) == 1
    assert words[0].raw == 1


def test_parser_ignores_invalid_chunks():
    parser = ArincFrameParser()
    words = parser.parse(b"\x00\x00\x00")
    assert words == []


class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.is_open = True
        self.in_waiting = 4
        self.buffer = b"ABCD"
        self.written = []

    def read(self, n):
        return self.buffer[:n]

    def write(self, payload):
        self.written.append(payload)

    def close(self):
        self.is_open = False


@pytest.fixture
def fake_serial(monkeypatch):
    fake = FakeSerial()
    monkeypatch.setattr("arinc429.drivers.serial", type("obj", (), {"Serial": FakeSerial})())
    return fake


def test_serial_open_close(fake_serial):
    t = SerialTransport("COM1")
    t.open()
    assert t.conn.is_open
    t.close()
    assert t.conn.is_open is False


def test_serial_read(fake_serial):
    t = SerialTransport("COM1")
    t.open()
    data = t.read(4)
    assert data == b"ABCD"


def test_serial_write(fake_serial):
    t = SerialTransport("COM1")
    t.open()
    t.write(b"XYZ")
    assert t.conn.written == [b"XYZ"]


@pytest.mark.parametrize("udp", [True, False])
def test_socket_open_close(udp, monkeypatch):
    if udp:
        transport = SocketTransport("127.0.0.1", 0, remote_host="127.0.0.1", remote_port=9999, udp=True)
        transport.open()
    else:
        transport = SocketTransport("127.0.0.1", 0, remote_host="127.0.0.1", remote_port=9999, udp=False)
        monkeypatch.setattr(socket.socket, "connect", lambda self, addr: None)
        transport.open()

    assert transport.sock is not None
    assert transport.sock.gettimeout() == 0.1
    transport.close()
    assert transport.sock is not None


def test_udp_write_without_remote():
    t = SocketTransport("127.0.0.1", 0, remote_host=None, remote_port=None, udp=True)
    t.open()
    t.write(b"abcd")


def test_udp_read_timeout():
    t = SocketTransport("127.0.0.1", 0, remote_host="127.0.0.1", remote_port=9999, udp=True)
    t.open()
    data = t.read(64)
    assert data == b""


def test_driver_lifecycle():
    bus = FakeBus()
    transport = FakeTransport()
    driver = DummyDriver(bus, transport)

    driver.connect()
    assert transport.opened is True
    assert driver.is_running is True

    driver.disconnect()
    assert transport.closed is True
    assert driver.is_running is False


def test_driver_rx_loop_publishes_words():
    bus = FakeBus()
    transport = FakeTransport([
        (1).to_bytes(4, "big"),
        b"",
    ])
    driver = DummyDriver(bus, transport)

    driver.connect()
    time.sleep(0.05)
    driver.disconnect()

    events = bus.events
    assert len(events) >= 1
    channel, word = events[0]
    assert channel == "HARDWARE_RX"
    assert isinstance(word, Word)
    assert word.raw == 1


def test_driver_error_propagation():
    class BadTransport(FakeTransport):
        def read(self, n):
            raise RuntimeError("boom")

    bus = FakeBus()
    transport = BadTransport()
    driver = DummyDriver(bus, transport)

    driver.connect()
    time.sleep(0.05)
    driver.disconnect()

    assert any(ch == "DRIVER_ERROR" for ch, _ in bus.events)
