import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def run_example(script: str):
    return subprocess.run(
        [sys.executable, str(EXAMPLES_DIR / script)], capture_output=True, text=True
    )


@pytest.mark.examples
@pytest.mark.parametrize(
    "script",
    [
        "flight_sim.py",
        "multi_fault_sim.py",
        "high_rate_stress_test.py",
        "datatypes_integration.py",
        "record_and_replay.py",
        "async_driver_demo.py",
    ],
)
def test_examples_run_without_crashing(script):
    result = run_example(script)
    assert result.returncode == 0, f"Example {script} crashed:\n{result.stderr}"


@pytest.mark.examples
def test_flight_sim_output_contains_expected_markers():
    result = run_example("flight_sim.py")
    out = result.stdout
    assert "Starting ARINC 429 Flight Simulation" in out
    assert "Phase 1" in out
    assert "Phase 2" in out
    assert "Phase 3" in out
    assert "Flight Simulation Audit Report" in out
    assert "Simulation completed successfully" in out


@pytest.mark.examples
def test_multi_fault_sim_output_contains_expected_markers():
    result = run_example("multi_fault_sim.py")
    out = result.stdout
    assert "Multi-Fault ARINC 429 Simulation" in out
    assert "Phase 1" in out
    assert "Phase 2" in out
    assert "Phase 3" in out
    assert "Multi-Fault Simulation Summary" in out
    assert "Simulation complete" in out


@pytest.mark.examples
def test_high_rate_stress_test_output_contains_expected_markers():
    result = run_example("high_rate_stress_test.py")
    out = result.stdout
    assert "High-Rate Stress Test" in out
    assert "Phase 1" in out
    assert "Phase 2" in out
    assert "High-Rate Stress Test Summary" in out
    assert "Simulation complete" in out


@pytest.mark.examples
def test_datatypes_integration_output_contains_expected_markers():
    result = run_example("datatypes_integration.py")
    out = result.stdout
    assert "Datatypes Integration Demo" in out
    assert "Final Decoded Altitude" in out
    assert "Final Decoded Frequency" in out
    assert "Datatypes decoding test passed successfully" in out


@pytest.mark.examples
def test_record_and_replay_output_contains_expected_markers():
    result = run_example("record_and_replay.py")
    out = result.stdout
    assert "Record & Replay Demo" in out
    assert "Replay complete" in out


@pytest.mark.examples
def test_async_driver_demo_output_contains_expected_markers():
    result = run_example("async_driver_demo.py")
    out = result.stdout
    assert "Transport opened." in out
    assert "Driver active." in out
    assert "Driver stopped." in out
