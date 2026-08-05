from __future__ import annotations

import time
import pytest
from pathlib import Path

from arinc429.sim import (
    ArincBus,
    VirtualNode,
    BusMonitor,
    FaultConfig,
    FaultyVirtualNode,
    stop_all,
)
from arinc429.word import Word


def make_word(label=0o123, data=0x55AA, parity_type=Word.ODD_PARITY):
    w = Word()
    w.label = label
    w.data = data
    w.parity_type = parity_type
    return Word.from_int(w.to_int(), parity_type)


def test_bus_attach_detach():
    bus = ArincBus()

    class Dummy:
        def on_word_received(self, word, source_id):
            pass

    d = Dummy()
    bus.attach(d)
    assert d in bus.listeners

    bus.detach(d)
    assert d not in bus.listeners


def test_bus_transmit_logs_and_routes():
    bus = ArincBus()
    received = []

    class L:
        def on_word_received(self, word, source_id):
            received.append((source_id, word))

    listener = L()
    bus.attach(listener)

    w = make_word()
    bus.transmit(w, "NODE1")

    assert len(bus.word_log) == 1
    ts, src, logged_word = bus.word_log[0]
    assert src == "NODE1"
    assert logged_word.to_int() == w.to_int()

    assert len(received) == 1
    assert received[0][0] == "NODE1"
    assert received[0][1].to_int() == w.to_int()


def test_virtualnode_periodic_transmission():
    bus = ArincBus()
    received = []

    class R:
        def on_word_received(self, word, source_id):
            received.append(source_id)

    r = R()
    bus.attach(r)

    node = VirtualNode("TX", bus)
    node.register_periodic_transmission(lambda: make_word(), rate_hz=20.0)
    node.start()

    time.sleep(0.15)
    node.stop()

    assert len(received) >= 2


def test_virtualnode_no_schedules():
    bus = ArincBus()
    node = VirtualNode("TX", bus)
    node.start()
    time.sleep(0.05)
    node.stop()

    assert len(bus.word_log) == 0


def test_virtualnode_multiple_schedules():
    bus = ArincBus()
    received = []

    class R:
        def on_word_received(self, word, source_id):
            received.append(source_id)

    bus.attach(R())

    node = VirtualNode("TX", bus)
    node.register_periodic_transmission(lambda: make_word(label=0o100), rate_hz=10)
    node.register_periodic_transmission(lambda: make_word(label=0o200), rate_hz=10)
    node.start()

    time.sleep(0.3)  # Increased from 0.2 to allow enough headroom for thread scheduling
    node.stop()

    assert len(received) >= 3
    labels = [w.label for _, _, w in bus.word_log]
    assert 0o100 in labels
    assert 0o200 in labels


def test_busmonitor_capture_and_parity():
    bus = ArincBus()
    mon = BusMonitor("MON", bus)

    good = make_word()
    bad_raw = good.to_int() ^ (1 << 31)
    bad = Word.from_int(bad_raw, good.parity_type)

    bus.transmit(good, "TX1")
    bus.transmit(bad, "TX2")

    assert len(mon.captured_words) == 2
    assert mon.parity_errors_detected == 1


def test_busmonitor_label_filter():
    bus = ArincBus()
    mon = BusMonitor("MON", bus)

    w1 = make_word(label=0o123)
    w2 = make_word(label=0o200)

    bus.transmit(w1, "TX")
    bus.transmit(w2, "TX")

    filtered = mon.get_traffic_by_label(0o123)
    assert len(filtered) == 1
    assert filtered[0].label == 0o123


def test_busmonitor_clear():
    bus = ArincBus()
    mon = BusMonitor("MON", bus)

    bus.transmit(make_word(), "TX")
    mon.clear()

    assert mon.captured_words == []
    assert mon.parity_errors_detected == 0


def test_faulty_drop_probability():
    bus = ArincBus()
    received = []

    class R:
        def on_word_received(self, word, source_id):
            received.append(word)

    bus.attach(R())

    cfg = FaultConfig(drop_probability=1.0)
    node = FaultyVirtualNode("FAULT", bus, cfg)

    node.transmit_with_faults(make_word())
    assert len(received) == 0


def test_faulty_parity_corruption():
    bus = ArincBus()
    received = []

    class R:
        def on_word_received(self, word, source_id):
            received.append(word)

    bus.attach(R())

    cfg = FaultConfig(corrupt_parity=True)
    node = FaultyVirtualNode("FAULT", bus, cfg)

    w = make_word()
    node.transmit_with_faults(w)

    assert len(received) == 1
    assert not received[0].parity_ok


def test_faulty_bit_flip():
    bus = ArincBus()
    received = []

    class R:
        def on_word_received(self, word, source_id):
            received.append(word)

    bus.attach(R())

    cfg = FaultConfig(bit_flip_probability=1.0)
    node = FaultyVirtualNode("FAULT", bus, cfg)

    w = make_word()
    node.transmit_with_faults(w)

    assert len(received) == 1
    assert received[0].to_int() != w.to_int()


def test_stop_all():
    bus = ArincBus()
    n1 = VirtualNode("N1", bus)
    n2 = VirtualNode("N2", bus)

    n1.register_periodic_transmission(lambda: make_word(), rate_hz=50)
    n2.register_periodic_transmission(lambda: make_word(), rate_hz=50)

    n1.start()
    n2.start()

    time.sleep(0.05)
    stop_all([n1, n2])

    assert not n1._running
    assert not n2._running
