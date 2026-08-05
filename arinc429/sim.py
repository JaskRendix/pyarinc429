from __future__ import annotations

import time
import threading
import random
from typing import Callable, Protocol, Any
from dataclasses import dataclass, field

from .word import Word


class BusListener(Protocol):
    """Protocol for anything that listens to bus traffic (Receivers, Monitors)."""
    def on_word_received(self, word: Word, source_id: str) -> None:
        ...


@dataclass
class ArincBus:
    """Central shared bus medium for routing ARINC 429 words between LRUs."""
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
        """Transmit a word onto the bus, logging it and broadcasting to all listeners."""
        timestamp = time.time()
        with self._lock:
            self.word_log.append((timestamp, source_id, word))
            for listener in self.listeners:
                listener.on_word_received(word, source_id)


class VirtualNode:
    """Represents a Line Replaceable Unit (LRU) like an ADC, IRS, or Flight Computer."""

    def __init__(self, node_id: str, bus: ArincBus) -> None:
        self.node_id = node_id
        self.bus = bus
        self.bus.attach(self)
        self._schedules: list[dict[str, Any]] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def register_periodic_transmission(self, word_generator: Callable[[], Word], rate_hz: float) -> None:
        """Schedule a periodic word broadcast at a specific frequency (Hz)."""
        interval = 1.0 / rate_hz
        self._schedules.append({
            "generator": word_generator,
            "interval": interval,
            "next_run": time.time() + interval
        })

    def on_word_received(self, word: Word, source_id: str) -> None:
        """Override in subclasses to handle incoming bus traffic (Receiver role)."""
        pass

    def start(self) -> None:
        """Start the node's internal transmission scheduler thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the node's transmission scheduler thread."""
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
            time.sleep(0.005)  # 5ms polling tick


class BusMonitor:
    """Passive databus monitor / sniffer to log traffic, filter labels, and catch parity errors."""

    def __init__(self, monitor_id: str, bus: ArincBus) -> None:
        self.monitor_id = monitor_id
        self.bus = bus
        self.bus.attach(self)
        self.captured_words: list[tuple[str, Word]] = []
        self.parity_errors_detected: int = 0

    def on_word_received(self, word: Word, source_id: str) -> None:
        """Passively inspect every word broadcasted on the bus."""
        self.captured_words.append((source_id, word))
        if not word.parity_ok:
            self.parity_errors_detected += 1

    def get_traffic_by_label(self, label: int) -> list[Word]:
        """Filter captured traffic by a specific ARINC label."""
        return [word for _, word in self.captured_words if word.label == label]

    def clear(self) -> None:
        self.captured_words.clear()
        self.parity_errors_detected = 0


@dataclass
class FaultConfig:
    """Configuration rules for injecting errors into bus transmissions."""
    drop_probability: float = 0.0      # Probability of dropping a word (0.0 to 1.0)
    corrupt_parity: bool = False       # Force invalid parity on transmitted words
    bit_flip_probability: float = 0.0  # Probability of flipping a random data bit


class FaultyVirtualNode(VirtualNode):
    """An LRU extension capable of injecting faults to test receiver robustness."""

    def __init__(self, node_id: str, bus: ArincBus, fault_config: FaultConfig) -> None:
        super().__init__(node_id, bus)
        self.fault_config = fault_config

    def transmit_with_faults(self, word: Word) -> None:
        """Apply configured fault injection rules before putting the word on the bus."""
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


def stop_all(nodes: list[VirtualNode]) -> None:
    """Convenience helper to cleanly stop a collection of virtual nodes."""
    for n in nodes:
        n.stop()
