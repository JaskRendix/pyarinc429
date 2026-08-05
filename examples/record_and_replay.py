from __future__ import annotations

import time
from pathlib import Path

from arinc429.builder import WordBuilder
from arinc429.recorder import BusRecorder, ReplayNode
from arinc429.sim import ArincBus, BusMonitor, VirtualNode, stop_all


def main() -> None:
    print("--- ARINC 429 Record & Replay Demo ---")
    log_file = Path("flight_recording.jsonl")

    #
    # PHASE 1 — RECORD LIVE TRAFFIC
    #
    print("\n[1] Recording live bus traffic...")
    bus = ArincBus()
    monitor = BusMonitor("RECORDER_MONITOR", bus)

    adc = VirtualNode("ADC_SOURCE", bus)
    adc.register_periodic_transmission(
        lambda: WordBuilder().label(0o203).data(0x1234).build(),
        rate_hz=20.0,
    )

    adc.start()
    time.sleep(1.0)  # record for 1 second
    stop_all([adc])

    BusRecorder.export_to_jsonl(monitor.captured_words, log_file)
    print(f"Recorded {len(monitor.captured_words)} words → {log_file}")

    #
    # PHASE 2 — REPLAY TRAFFIC
    #
    print("\n[2] Replaying recorded traffic at 2× speed...")
    replay_bus = ArincBus()
    replay_monitor = BusMonitor("REPLAY_MONITOR", replay_bus)

    player = ReplayNode(log_file, replay_bus, speed_multiplier=2.0)
    player.play()

    print(
        f"Replay complete. Auditor captured {len(replay_monitor.captured_words)} words."
    )

    #
    # CLEANUP
    #
    log_file.unlink(missing_ok=True)
    print("\nDemo finished. Temporary log file removed.")


if __name__ == "__main__":
    main()
