from __future__ import annotations

import asyncio
import json
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

from .drivers import ArincFrameParser
from .word import Word

if TYPE_CHECKING:
    pass


class BusListener(Protocol):
    def on_word_received(self, word: Word, source_id: str) -> None:
        ...


@dataclass
class ArincBus:
    listeners: list[BusListener] = field(default_factory=list)
    word_log: list[tuple[float, str, Word]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def attach(self, listener: BusListener) -> None:
        with self._lock:
            if listener not in self.listeners:
                self.listeners.append(listener)

    def detach(self, listener: BusListener) -> None:
        with self._lock:
            if listener in self.listeners:
                self.listeners.remove(listener)

    def transmit(self, word: Word, source_id: str) -> None:
        timestamp = time.time()
        with self._lock:
            self.word_log.append((timestamp, source_id, word))
            for listener in self.listeners:
                listener.on_word_received(word, source_id)

    def publish(self, word: Word, source_id: str) -> None:
        self.transmit(word, source_id)


class VirtualNode:

    def __init__(self, node_id: str, bus: ArincBus) -> None:
        self.node_id = node_id
        self.bus = bus
        self.bus.attach(self)
        self._schedules: list[dict[str, Any]] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def register_periodic_transmission(self, word_generator: Callable[[], Word], rate_hz: float) -> None:
        interval = 1.0 / rate_hz
        self._schedules.append({
            "generator": word_generator,
            "interval": interval,
            "next_run": time.time() + interval
        })

    def on_word_received(self, word: Word, source_id: str) -> None:
        pass

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run_loop(self) -> None:
        while self._running:
            now = time.time()
            for sched in self._schedules:
                if now >= sched["next_run"]:
                    word = sched["generator"]()
                    self.bus.transmit(word, self.node_id)
                    sched["next_run"] = now + sched["interval"]
            time.sleep(0.005)


class BusMonitor:

    def __init__(self, monitor_id: str, bus: ArincBus) -> None:
        self.monitor_id = monitor_id
        self.bus = bus
        self.bus.attach(self)
        self.captured_words: list[tuple[float, Word, str]] = []
        self.parity_errors_detected: int = 0

    def on_word_received(self, word: Word, source_id: str) -> None:
        timestamp = time.time()
        self.captured_words.append((timestamp, word, source_id))
        if not word.parity_ok:
            self.parity_errors_detected += 1

    def get_traffic_by_label(self, label: int) -> list[Word]:
        return [word for _, word, _ in self.captured_words if word.label == label]

    def clear(self) -> None:
        self.captured_words.clear()
        self.parity_errors_detected = 0


@dataclass
class FaultConfig:
    drop_probability: float = 0.0
    corrupt_parity: bool = False
    bit_flip_probability: float = 0.0


class FaultyVirtualNode(VirtualNode):

    def __init__(self, node_id: str, bus: ArincBus, fault_config: FaultConfig) -> None:
        super().__init__(node_id, bus)
        self.fault_config = fault_config

    def transmit_with_faults(self, word: Word) -> None:
        if self.fault_config.drop_probability > 0.0:
            if random.random() < self.fault_config.drop_probability:
                return

        if self.fault_config.bit_flip_probability > 0.0:
            raw = word.to_int()
            for bit_pos in range(32):
                if random.random() < self.fault_config.bit_flip_probability:
                    raw ^= (1 << bit_pos)
            word = Word.from_int(raw, word.parity_type)

        if self.fault_config.corrupt_parity:
            raw = word.to_int()
            raw ^= (1 << 31)
            word = Word.from_int(raw, word.parity_type)

        self.bus.transmit(word, self.node_id)

    def _run_loop(self) -> None:
        while self._running:
            now = time.time()
            for sched in self._schedules:
                if now >= sched["next_run"]:
                    word = sched["generator"]()
                    self.transmit_with_faults(word)
                    sched["next_run"] = now + sched["interval"]
            time.sleep(0.005)


class BusRecorder:

    @staticmethod
    def export_to_jsonl(captured_words: list[tuple[float, Word, str]], filepath: Path | str) -> None:
        path = Path(filepath)
        with path.open("w", encoding="utf-8") as f:
            for timestamp, word, source_id in captured_words:
                record = {
                    "timestamp": timestamp,
                    "word_int": word.to_int(),
                    "parity_type": word.parity_type,
                    "source_id": source_id,
                }
                f.write(json.dumps(record) + "\n")


class ReplayNode:

    def __init__(self, filepath: Path | str, bus: ArincBus, speed_multiplier: float = 1.0) -> None:
        self.filepath = Path(filepath)
        self.bus = bus
        self.speed_multiplier = speed_multiplier
        self._running = False

    def play(self) -> None:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Record file not found: {self.filepath}")

        with self.filepath.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return

        self._running = True
        records = [json.loads(line) for line in lines]

        start_real_time = time.time()
        start_log_time = records[0]["timestamp"]

        for rec in records:
            if not self._running:
                break

            log_delta = rec["timestamp"] - start_log_time
            target_real_delay = log_delta / self.speed_multiplier

            elapsed_real = time.time() - start_real_time
            sleep_time = target_real_delay - elapsed_real

            if sleep_time > 0:
                time.sleep(sleep_time)

            word = Word.from_int(rec["word_int"], rec["parity_type"])
            self.bus.publish(word, source_id=f"REPLAY:{rec['source_id']}")

    def stop(self) -> None:
        self._running = False


class AsyncBusTransportDriver(BusListener):

    def __init__(self, bus: ArincBus, transport: Any, source_id: str = "HW_DEVICE") -> None:
        self.bus = bus
        self.transport = transport
        self.parser = ArincFrameParser()
        self.source_id = source_id

        self._task: asyncio.Task[None] | None = None
        self._running = False

        self.bus.attach(self)

    async def connect(self) -> None:
        self.transport.open()
        self._running = True
        self._task = asyncio.create_task(self._rx_loop())

    async def disconnect(self) -> None:
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.transport.close()

    def on_word_received(self, word: Word, source_id: str) -> None:
        if source_id == self.source_id:
            return

        try:
            payload = word.raw.to_bytes(4, "big")
            self.transport.write(payload)
        except Exception:
            error_word = Word.from_int(0)
            self.bus.transmit(error_word, f"DRIVER_ERROR:{self.source_id}")

    async def _rx_loop(self) -> None:
        while self._running:
            try:
                data = self.transport.read(64)

                if data:
                    for word in self.parser.parse(data):
                        self.bus.transmit(word, self.source_id)
                else:
                    await asyncio.sleep(0.001)

            except Exception:
                error_word = Word.from_int(0)
                self.bus.transmit(error_word, f"DRIVER_ERROR:{self.source_id}")
                await asyncio.sleep(0.01)


def stop_all(nodes: list[VirtualNode]) -> None:
    for n in nodes:
        n.stop()
