from __future__ import annotations

import json
import time
import threading

import pytest

from arinc429.sim import (
    ArincBus,
    BusMonitor,
    BusRecorder,
    ReplayNode,
)
from arinc429.word import Word


def make_word(label=0o123, data=0x55AA, parity_type=Word.ODD_PARITY):
    w = Word()
    w.label = label
    w.data = data
    w.parity_type = parity_type
    return Word.from_int(w.to_int(), parity_type)


def test_busrecorder_export_jsonl(tmp_path):
    bus = ArincBus()
    mon = BusMonitor("MON", bus)

    w = make_word(label=0o123, data=0x55AA)
    bus.transmit(w, "SRC")

    outfile = tmp_path / "log.jsonl"
    BusRecorder.export_to_jsonl(mon.captured_words, outfile)

    lines = outfile.read_text().splitlines()
    assert len(lines) == 1

    rec = json.loads(lines[0])
    assert rec["word_int"] == w.to_int()
    assert rec["source_id"] == "SRC"
    assert isinstance(rec["timestamp"], float)
    assert rec["parity_type"] == w.parity_type


def test_replaynode_basic(tmp_path):
    w = make_word()
    outfile = tmp_path / "log.jsonl"

    BusRecorder.export_to_jsonl([(time.time(), w, "SRC")], outfile)

    replay_bus = ArincBus()
    replay_mon = BusMonitor("REPLAY_MON", replay_bus)

    player = ReplayNode(outfile, replay_bus)
    player.play()

    assert len(replay_mon.captured_words) == 1
    _, replayed_word, src = replay_mon.captured_words[0]

    assert replayed_word.to_int() == w.to_int()
    assert src.startswith("REPLAY:")


def test_replaynode_timing(tmp_path):
    w1 = make_word()
    w2 = make_word()

    t0 = time.time()
    records = [
        (t0, w1, "SRC"),
        (t0 + 0.2, w2, "SRC"),
    ]

    outfile = tmp_path / "log.jsonl"
    BusRecorder.export_to_jsonl(records, outfile)

    replay_bus = ArincBus()
    replay_mon = BusMonitor("REPLAY_MON", replay_bus)

    player = ReplayNode(outfile, replay_bus, speed_multiplier=1.0)

    start = time.time()
    player.play()
    end = time.time()

    assert end - start >= 0.2
    assert len(replay_mon.captured_words) == 2


def test_replaynode_stop(tmp_path):
    w = make_word()
    outfile = tmp_path / "log.jsonl"

    records = [(time.time() + i * 0.05, w, "SRC") for i in range(20)]
    BusRecorder.export_to_jsonl(records, outfile)

    replay_bus = ArincBus()
    replay_mon = BusMonitor("REPLAY_MON", replay_bus)

    player = ReplayNode(outfile, replay_bus)

    t = threading.Thread(target=player.play)
    t.start()

    time.sleep(0.1)
    player.stop()
    t.join()

    assert len(replay_mon.captured_words) < 20


def test_record_and_replay_integration(tmp_path):
    bus = ArincBus()
    mon = BusMonitor("MON", bus)

    w = make_word()
    bus.transmit(w, "SRC")

    outfile = tmp_path / "log.jsonl"
    BusRecorder.export_to_jsonl(mon.captured_words, outfile)

    replay_bus = ArincBus()
    replay_mon = BusMonitor("REPLAY_MON", replay_bus)

    player = ReplayNode(outfile, replay_bus)
    player.play()

    assert len(replay_mon.captured_words) == 1
    _, replayed_word, src = replay_mon.captured_words[0]

    assert replayed_word.to_int() == w.to_int()
    assert src.startswith("REPLAY:")
