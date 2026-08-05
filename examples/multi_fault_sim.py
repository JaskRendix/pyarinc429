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


class FlightDirector(VirtualNode):
    """Flight Director that consumes multiple ARINC labels and detects anomalies."""

    def __init__(self, node_id: str, bus: ArincBus) -> None:
        super().__init__(node_id, bus)
        self.altitude_log: list[int] = []
        self.heading_log: list[int] = []
        self.anomalies: list[str] = []

    def on_word_received(self, word: Word, source_id: str) -> None:
        if not word.parity_ok:
            self.anomalies.append(f"Parity error from {source_id}")
            return

        if word.label == 0o203:  # Altitude
            self.altitude_log.append(word.data)
        elif word.label == 0o310:  # Heading
            self.heading_log.append(word.data)
        else:
            # Unexpected label
            self.anomalies.append(f"Unexpected label {oct(word.label)} from {source_id}")


def main() -> None:
    print("--- Multi-Fault ARINC 429 Simulation ---")

    bus = ArincBus()
    monitor = BusMonitor("SYSTEM_MONITOR", bus)

    # Normal avionics nodes
    adc = VirtualNode("ADC", bus)
    adc.register_periodic_transmission(
        lambda: WordBuilder().label(0o203).data(0x2000).build(), rate_hz=12.0
    )

    irs = VirtualNode("IRS", bus)
    irs.register_periodic_transmission(
        lambda: WordBuilder().label(0o310).data(0x0A00).build(), rate_hz=18.0
    )

    fd = FlightDirector("FLIGHT_DIRECTOR", bus)

    nodes = [adc, irs, fd]

    # Faulty node #1: Parity corruption + bit flips
    cfg1 = FaultConfig(
        corrupt_parity=True,
        bit_flip_probability=0.05,
        drop_probability=0.0,
    )
    faulty1 = FaultyVirtualNode("FAULTY_SENSOR_1", bus, cfg1)
    faulty1.register_periodic_transmission(
        lambda: WordBuilder().label(0o203).data(0xEEEE).build(), rate_hz=15.0
    )
    nodes.append(faulty1)

    # Faulty node #2: High drop rate + occasional wrong labels
    cfg2 = FaultConfig(
        corrupt_parity=False,
        bit_flip_probability=0.0,
        drop_probability=0.4,
    )
    faulty2 = FaultyVirtualNode("FAULTY_SENSOR_2", bus, cfg2)

    def wrong_label_generator():
        # Randomly send altitude or heading — or a completely wrong label
        label = random.choice([0o203, 0o310, 0o777])
        return WordBuilder().label(label).data(0x1234).build()

    faulty2.register_periodic_transmission(wrong_label_generator, rate_hz=10.0)
    nodes.append(faulty2)

    # Faulty node #3: Goes silent after 1 second
    silent_node = VirtualNode("SILENT_NODE", bus)
    silent_node.register_periodic_transmission(
        lambda: WordBuilder().label(0o310).data(0x9999).build(), rate_hz=8.0
    )
    nodes.append(silent_node)

    # Start all nodes
    for n in nodes:
        n.start()

    print("[Phase 1] Running simulation with multiple faults...")
    time.sleep(1.0)

    print("[Phase 2] SILENT_NODE stops transmitting...")
    silent_node.stop()

    time.sleep(1.5)

    print("[Phase 3] Shutting down...")
    stop_all(nodes)

    # Summary
    print("\n--- Multi-Fault Simulation Summary ---")
    print(f"Total bus traffic captured: {len(monitor.captured_words)}")
    print(f"Total parity errors: {monitor.parity_errors_detected}")
    print(f"FD altitude messages: {len(fd.altitude_log)}")
    print(f"FD heading messages: {len(fd.heading_log)}")
    print(f"FD anomalies detected: {len(fd.anomalies)}")
    for a in fd.anomalies:
        print("  -", a)

    print("Simulation complete.")


if __name__ == "__main__":
    main()
