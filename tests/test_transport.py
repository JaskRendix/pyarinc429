from __future__ import annotations

import asyncio

import pytest

from arinc429.drivers import ArincFrameParser
from arinc429.sim import ArincBus
from arinc429.transport import AsyncBusTransportDriver
from arinc429.word import Word


class DummyTransport:
    def __init__(self, read_chunks=None, fail_write=False, fail_read=False):
        self.opened = False
        self.closed = False
        self.writes = []
        self.read_chunks = read_chunks or []
        self.fail_write = fail_write
        self.fail_read = fail_read

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def write(self, data: bytes):
        if self.fail_write:
            raise RuntimeError("write failure")
        self.writes.append(data)

    def read(self, size: int) -> bytes:
        if self.fail_read:
            raise RuntimeError("read failure")
        if not self.read_chunks:
            return b""
        return self.read_chunks.pop(0)


@pytest.mark.asyncio
async def test_driver_connect_and_disconnect():
    bus = ArincBus()
    transport = DummyTransport()
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW")

    await driver.connect()
    assert transport.opened is True
    assert driver._running is True
    assert driver._task is not None

    await driver.disconnect()
    assert transport.closed is True
    assert driver._running is False


@pytest.mark.asyncio
async def test_driver_ignores_self_originated_words():
    bus = ArincBus()
    transport = DummyTransport()
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW")

    await driver.connect()

    w = Word.from_int(0x12345678)

    driver.on_word_received(w, "HW")
    assert transport.writes == []

    await driver.disconnect()


@pytest.mark.asyncio
async def test_driver_transmits_outbound_words():
    bus = ArincBus()
    transport = DummyTransport()
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW")

    await driver.connect()

    w = Word.from_int(0x11223344)

    driver.on_word_received(w, "SIM_NODE")
    assert transport.writes == [b"\x11\x22\x33\x44"]

    await driver.disconnect()


@pytest.mark.asyncio
async def test_driver_rx_loop_injects_words_into_bus():
    parser = ArincFrameParser()
    word = Word.from_int(0xAABBCCDD)
    frame = word.to_int().to_bytes(4, "big")

    bus = ArincBus()
    transport = DummyTransport(read_chunks=[frame])
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW")

    received = []

    class Listener:
        def on_word_received(self, w, src):
            received.append((w.to_int(), src))

    bus.attach(Listener())

    await driver.connect()
    await asyncio.sleep(0.01)
    await driver.disconnect()

    assert received == [(0xAABBCCDD, "HW")]


@pytest.mark.asyncio
async def test_driver_rx_loop_empty_reads():
    bus = ArincBus()
    transport = DummyTransport(read_chunks=[b"", b"", b""])
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW")

    await driver.connect()
    await asyncio.sleep(0.01)
    await driver.disconnect()

    assert transport.closed is True


@pytest.mark.asyncio
async def test_driver_error_callback_on_write_failure():
    errors = []

    def cb(err, src):
        errors.append((str(err), src))

    bus = ArincBus()
    transport = DummyTransport(fail_write=True)
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW", error_callback=cb)

    await driver.connect()

    w = Word.from_int(0xDEADBEEF)

    driver.on_word_received(w, "SIM_NODE")
    await driver.disconnect()

    assert errors == [("write failure", "HW")]


@pytest.mark.asyncio
async def test_driver_error_callback_on_read_failure():
    errors = []

    def cb(err, src):
        errors.append((str(err), src))

    bus = ArincBus()
    transport = DummyTransport(fail_read=True)
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW", error_callback=cb)

    await driver.connect()
    await asyncio.sleep(0.02)
    await driver.disconnect()

    assert errors != []
    assert errors[0][1] == "HW"


@pytest.mark.asyncio
async def test_driver_task_cancellation():
    bus = ArincBus()
    transport = DummyTransport()
    driver = AsyncBusTransportDriver(bus, transport, source_id="HW")

    await driver.connect()
    assert driver._task is not None

    await driver.disconnect()
    assert driver._task.cancelled() is True
