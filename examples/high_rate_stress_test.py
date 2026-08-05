from __future__ import annotations

import time
import random

from arinc429.sim import (
    ArincBus,
    VirtualNode,
    BusMonitor,
    FaultConfig,
    FaultyVirtualNode,
    stop_all,
)
from arinc429.builder import WordBuilder
from arinc429.word import Word


class StressReceiver(VirtualNode):
    """Receiver that counts messages and detects overload conditions."""

    def __init__(self, node_id: str, bus: ArincBus) -> None:
        super().__init__(node_id, bus)
        self.total_received = 0
        self.parity_errors = 0

    def on_word_received(self, word: Word, source_id: str) -> None:
        self.total_received += 1
        if not word.parity_ok:
            self.parity_errors += 1


def main() -> None:
    print("--- ARINC 429 High-Rate Stress Test ---")

    bus = ArincBus()
    monitor = BusMonitor("SYSTEM_MONITOR", bus)
    receiver = StressReceiver("STRESS_RECEIVER", bus)

    nodes = [receiver]

    # High-rate ADC (100 Hz)
    adc = VirtualNode("ADC_FAST", bus)
    adc.register_periodic_transmission(
        lambda: WordBuilder().label(0o203).data(random.randint(0, 0xFFFF)).build(),
        rate_hz=100.0,
    )
    nodes.append(adc)

    # High-rate IRS (200 Hz)
    irs = VirtualNode("IRS_FAST", bus)
    irs.register_periodic_transmission(
        lambda: WordBuilder().label(0o310).data(random.randint(0, 0xFFFF)).build(),
        rate_hz=200.0,
    )
    nodes.append(irs)

    # Faulty node at 150 Hz with bit flips + parity corruption
    cfg_fault = FaultConfig(
        corrupt_parity=True,
        bit_flip_probability=0.02,
        drop_probability=0.05,
    )
    faulty = FaultyVirtualNode("FAULTY_ULTRA", bus, cfg_fault)
    faulty.register_periodic_transmission(
        lambda: WordBuilder().label(0o777).data(random.randint(0, 0xFFFF)).build(),
        rate_hz=150.0,
    )
    nodes.append(faulty)

    # Extreme-rate node (500 Hz)
    extreme = VirtualNode("EXTREME_RATE_NODE", bus)
    extreme.register_periodic_transmission(
        lambda: WordBuilder().label(0o123).data(random.randint(0, 0xFFFF)).build(),
        rate_hz=500.0,
    )
    nodes.append(extreme)

    # Start all nodes
    for n in nodes:
        n.start()

    print("[Phase 1] Running high-rate stress test for 2 seconds...")
    time.sleep(2.0)

    print("[Phase 2] Shutting down...")
    stop_all(nodes)

    # Summary
    print("\n--- High-Rate Stress Test Summary ---")
    print(f"Total bus traffic captured: {len(monitor.captured_words)}")
    print(f"Total parity errors: {monitor.parity_errors_detected}")
    print(f"Receiver processed messages: {receiver.total_received}")
    print(f"Receiver parity errors: {receiver.parity_errors}")
    print("Simulation complete.")


if __name__ == "__main__":
    main()
