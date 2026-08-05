from __future__ import annotations

import time
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


class FlightManagementComputer(VirtualNode):
    """FMC that listens to bus traffic and logs critical flight parameters."""

    def __init__(self, node_id: str, bus: ArincBus) -> None:
        super().__init__(node_id, bus)
        self.altitude_readings: list[int] = []
        self.heading_readings: list[int] = []

    def on_word_received(self, word: Word, source_id: str) -> None:
        if not word.parity_ok:
            print(f"[{self.node_id}] WARNING: Parity error detected from source {source_id}!")
            return

        if word.label == 0o203:  # Barometric Altitude label example
            self.altitude_readings.append(word.data)
            print(f"[{self.node_id}] Received Altitude from {source_id}: Data = {hex(word.data)}")
        elif word.label == 0o310:  # Heading label example
            self.heading_readings.append(word.data)
            print(f"[{self.node_id}] Received Heading from {source_id}: Data = {hex(word.data)}")


def main() -> None:
    print("--- Starting ARINC 429 Flight Simulation Example ---")

    bus = ArincBus()
    monitor = BusMonitor("SYSTEM_BUS_MONITOR", bus)

    # 1. Instantiate Avionics Units
    adc = VirtualNode("AIR_DATA_COMPUTER", bus)
    adc.register_periodic_transmission(
        lambda: WordBuilder().label(0o203).data(0x25A0).build(), rate_hz=10.0
    )

    irs = VirtualNode("INERTIAL_REFERENCE_SYSTEM", bus)
    irs.register_periodic_transmission(
        lambda: WordBuilder().label(0o310).data(0x0B4C).build(), rate_hz=20.0
    )

    fmc = FlightManagementComputer("FLIGHT_MANAGEMENT_COMPUTER", bus)

    active_nodes = [adc, irs, fmc]

    # Start normal operations
    for node in active_nodes:
        node.start()

    print("\n[Phase 1] Normal flight operation running for 1.5 seconds...")
    time.sleep(1.5)

    # 2. Introduce a Faulty Sensor partway through
    print("\n[Phase 2] Injecting sensor failure: Introducing Faulty Altitude Sensor...")
    fault_cfg = FaultConfig(corrupt_parity=True, drop_probability=0.2)
    faulty_adc = FaultyVirtualNode("FAULTY_ADC", bus, fault_cfg)
    faulty_adc.register_periodic_transmission(
        lambda: WordBuilder().label(0o203).data(0xEEEE).build(), rate_hz=15.0
    )
    
    faulty_adc.start()
    active_nodes.append(faulty_adc)

    time.sleep(1.5)

    # 3. Shutdown all nodes cleanly
    print("\n[Phase 3] Shutting down simulation...")
    stop_all(active_nodes)

    # 4. Print Audit Summary
    print("\n--- Flight Simulation Audit Report ---")
    print(f"Total words captured by Bus Monitor : {len(monitor.captured_words)}")
    print(f"Total parity errors caught on bus   : {monitor.parity_errors_detected}")
    print(f"Total altitude messages processed   : {len(fmc.altitude_readings)}")
    print(f"Total heading messages processed    : {len(fmc.heading_readings)}")
    print("Simulation completed successfully.")


if __name__ == "__main__":
    main()
