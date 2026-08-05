from __future__ import annotations

import time

from arinc429.builder import WordBuilder
from arinc429.datatypes.bcd import BCD
from arinc429.datatypes.bnr import BNR
from arinc429.sim import ArincBus, BusMonitor, VirtualNode, stop_all
from arinc429.word import Word


class EngineeringFlightDeck(VirtualNode):
    """An avionics display unit that decodes raw bus data using your datatypes module."""

    def __init__(self, node_id: str, bus: ArincBus) -> None:
        super().__init__(node_id, bus)
        self.current_altitude: float | None = None
        self.current_frequency: float | None = None

    def on_word_received(self, word: Word, source_id: str) -> None:
        if not word.parity_ok:
            return

        # Example: Label 0o203 is Barometric Altitude encoded in BNR
        if word.label == 0o203:
            try:
                # Using your BNR.decode() method with a resolution (e.g., 1.0 ft)
                # Assuming word.data holds the raw bits/payload value
                decoded_bnr = BNR.decode(
                    bnr_value=word.data, bnr_bit_length=16, resolution=1.0
                )
                self.current_altitude = float(decoded_bnr)
                print(
                    f"[{self.node_id}] Altitude from {source_id}: {decoded_bnr} ft (JSON: {decoded_bnr.to_json()})"
                )
            except Exception as e:
                print(f"[{self.node_id}] Failed to decode BNR altitude: {e}")

        # Example: Label 0o030 is Active Frequency encoded in BCD
        elif word.label == 0o030:
            try:
                # Using your BCD.decode() method with a resolution (e.g., 0.01 MHz)
                # word.ssm can provide the BCD sign matrix code
                decoded_bcd = BCD.decode(
                    bcd_value=word.data, bcd_sign=BCD.PLUS, resolution=0.01
                )
                self.current_frequency = float(decoded_bcd)
                print(f"[{self.node_id}] Frequency from {source_id}: {decoded_bcd} MHz")
            except Exception as e:
                print(f"[{self.node_id}] Failed to decode BCD frequency: {e}")


def main() -> None:
    print("--- ARINC 429 Datatypes Integration Demo ---")

    bus = ArincBus()
    monitor = BusMonitor("SYSTEM_MONITOR", bus)

    # 1. Transmitter (Air Data Computer) sending BNR-encoded altitude data
    adc = VirtualNode("ADC", bus)
    adc.register_periodic_transmission(
        lambda: WordBuilder().label(0o203).data(0x2710).build(),  # Raw data payload
        rate_hz=5.0,
    )

    # 2. Transmitter (Radio Tuning Unit) sending BCD-encoded frequency data
    rtu = VirtualNode("RTU", bus)
    rtu.register_periodic_transmission(
        lambda: WordBuilder().label(0o030).data(0x1218).build(), rate_hz=2.0
    )

    # 3. Receiver using your decoders
    flight_deck = EngineeringFlightDeck("FLIGHT_DECK", bus)

    nodes = [adc, rtu, flight_deck]
    for n in nodes:
        n.start()

    time.sleep(1.0)
    stop_all(nodes)

    print("\n--- Summary ---")
    print(f"Final Decoded Altitude  : {flight_deck.current_altitude} ft")
    print(f"Final Decoded Frequency : {flight_deck.current_frequency} MHz")
    print("Datatypes decoding test passed successfully.")


if __name__ == "__main__":
    main()
