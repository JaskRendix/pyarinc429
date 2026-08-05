# **ARINC 429 Examples**

This directory contains runnable examples demonstrating how the ARINC 429 simulation bus, virtual nodes, fault injection, hardware drivers, and replay tools operate together.  
Each file focuses on a specific integration or test scenario.

---

## **datatypes_integration.py**
Shows how ARINC 429 datatypes map into `Word` objects and how decoded fields interact with the simulation bus.

Key points:
- Demonstrates label, SDI, SSM, and numeric field extraction.
- Sends structured words from virtual nodes.
- Verifies decoding logic against the ICD.
- Useful for confirming datatype correctness and end‑to‑end encoding/decoding.

---

## **flight_sim.py**
Runs a small flight‑data simulation using multiple virtual nodes.

Key points:
- Generates ARINC 429 words representing aircraft parameters (altitude, airspeed, attitude, engine data).
- Uses periodic transmission scheduling.
- Demonstrates multi‑node interaction on the bus.
- Useful for validating bus behavior under realistic flight‑data patterns.

---

## **high_rate_stress_test.py**
Pushes the bus and driver layer under high transmission rates.

Key points:
- Creates nodes transmitting at maximum ARINC 429 rates.
- Measures bus throughput and listener performance.
- Exercises driver stability and parser correctness under load.
- Useful for identifying bottlenecks in transport, parsing, or listener dispatch.

---

## **multi_fault_sim.py**
Exercises fault injection using `FaultyVirtualNode`.

Key points:
- Applies bit flips, parity corruption, and probabilistic word drops.
- Sends corrupted traffic into the bus.
- Allows monitors to detect parity errors and abnormal patterns.
- Useful for robustness testing and validating error‑handling logic.

---

## **record_and_replay.py**
Captures ARINC 429 traffic and replays it with original timing.

Key points:
- Uses `BusRecorder` to export traffic to JSONL.
- Uses `ReplayNode` to reproduce timing and sequence.
- Supports speed scaling via `speed_multiplier`.
- Useful for regression testing, deterministic playback, and hardware‑in‑the‑loop scenarios.
