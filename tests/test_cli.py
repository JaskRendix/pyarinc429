from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
import pytest

from arinc429.word import Word


def run_cli(args):
    """Run the pyarinc CLI and return subprocess.CompletedProcess."""
    return subprocess.run(
        ["pyarinc", *args],
        capture_output=True,
        text=True
    )


@pytest.mark.parametrize("raw_word", ["0x9c000c26", "2617243558"])
@pytest.mark.parametrize("parity", ["odd", "even"])
@pytest.mark.parametrize("profile", ["adc", "irs", "all"])
def test_decode_basic(raw_word, parity, profile):
    result = run_cli(["decode", raw_word, "--parity", parity, "--profile", profile])
    assert result.returncode == 0
    out = result.stdout

    assert "Label (oct)" in out
    assert "SDI" in out
    assert "SSM" in out
    assert "DATA bits" in out


def test_decode_json():
    result = run_cli(["decode", "0x9c000c26", "--json"])
    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert "raw" in data
    assert "label" in data
    assert "sdi" in data
    assert "ssm" in data
    assert "data" in data
    assert "decoded_fields" in data
    assert "errors" in data


def test_decode_invalid():
    result = run_cli(["decode", "not_a_number"])
    assert result.returncode != 0
    assert "Invalid integer/hex format" in result.stdout


@pytest.mark.parametrize("payload", ["HELLO", "A", "XYZ"])
def test_arinc615_encode_string(payload):
    result = run_cli(["arinc615-encode", payload])
    assert result.returncode == 0
    assert "Generated" in result.stdout
    assert "0x" in result.stdout


def test_arinc615_encode_empty_string():
    result = run_cli(["arinc615-encode", ""])
    assert result.returncode != 0
    assert "must be provided" in result.stdout


def test_arinc615_encode_file(tmp_path):
    p = tmp_path / "payload.bin"
    p.write_bytes(b"HELLO")

    result = run_cli(["arinc615-encode", "--file", str(p)])
    assert result.returncode == 0
    assert "Generated" in result.stdout


def test_arinc615_encode_file_not_found():
    result = run_cli(["arinc615-encode", "--file", "no_such_file.bin"])
    assert result.returncode != 0
    assert "Error reading file" in result.stdout


def test_arinc615_encode_output_file(tmp_path):
    p = tmp_path / "payload.bin"
    p.write_bytes(b"HELLO")

    out = tmp_path / "words.json"

    result = run_cli(["arinc615-encode", "--file", str(p), "--output", str(out)])
    assert result.returncode == 0
    assert out.exists()

    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert all(isinstance(x, str) for x in data)
    assert all(x.startswith("0x") for x in data)


@pytest.mark.parametrize("message", ["HELLO", "A", "ABCDE", "123456789"])
def test_williamsburg_simulate_basic(message):
    result = run_cli(["williamsburg-simulate", message])
    assert result.returncode == 0
    assert "Successfully reconstructed payload" in result.stdout
    assert message in result.stdout


def test_williamsburg_simulate_trace():
    result = run_cli(["williamsburg-simulate", "HELLO", "--trace"])
    assert result.returncode == 0

    out = result.stdout
    assert "SAL:" in out
    assert "RTS:" in out
    assert "BLOCK:" in out
    assert "ACK:" in out


def test_missing_command():
    result = run_cli([])
    assert result.returncode == 2


def test_unknown_command():
    result = run_cli(["no_such_command"])
    assert result.returncode != 0
    assert "invalid choice" in result.stderr.lower() or "usage" in result.stderr.lower()


def test_help():
    result = run_cli(["--help"])
    assert result.returncode == 0

    out = result.stdout
    assert "decode" in out
    assert "arinc615-encode" in out
    assert "williamsburg-simulate" in out


def test_load_icd_success(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps({
            "labels": [
                {
                    "label": "0o203",
                    "name": "Pressure Altitude",
                    "system": "ADC",
                    "category": "Air Data",
                    "direction": "Source",
                    "description": "Test description"
                }
            ]
        }),
        encoding="utf-8"
    )

    result = run_cli(["load-icd", str(icd_file)])
    assert result.returncode == 0
    assert "Successfully loaded 1 label definitions" in result.stdout


def test_load_icd_multiple(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps({
            "labels": [
                {"label": "0o203", "name": "A", "system": "ADC", "category": "Air Data"},
                {"label": "0x45", "name": "B", "system": "IRS", "category": "Nav"},
                {"label": 123, "name": "C", "system": "ADC", "category": "Misc"},
            ]
        }),
        encoding="utf-8"
    )

    result = run_cli(["load-icd", str(icd_file)])
    assert result.returncode == 0
    assert "Successfully loaded 3 label definitions" in result.stdout


def test_load_icd_file_not_found():
    result = run_cli(["load-icd", "no_such_icd.json"])
    assert result.returncode != 0
    assert "Error loading ICD file" in result.stdout


def test_load_icd_invalid_json(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text("{ invalid json", encoding="utf-8")

    result = run_cli(["load-icd", str(icd_file)])
    assert result.returncode != 0
    assert "Error loading ICD file" in result.stdout


def test_simulate_basic():
    result = run_cli(["simulate", "--duration", "0.5"])
    assert result.returncode == 0

    out = result.stdout
    assert "Initializing ARINC 429 Bus Simulation" in out
    assert "Simulation running for" in out
    assert "Simulation Summary" in out
    assert "Total words captured" in out
    assert "Parity errors detected" in out

    assert "203" in out or "0o203" in out
    assert "310" in out or "0o310" in out


def test_simulate_faulty_node():
    result = run_cli(["simulate", "--duration", "0.5", "--faulty"])
    assert result.returncode == 0

    out = result.stdout
    assert "FAULTY_SENSOR" in out
    assert "Fault injection enabled" in out
    assert "101" in out or "0o101" in out

    lines = out.splitlines()
    parity_line = next((l for l in lines if "Parity errors detected" in l), None)
    assert parity_line is not None

    count = int(parity_line.split(":")[1].strip())
    assert count >= 1


def test_simulate_duration_effect():
    short = run_cli(["simulate", "--duration", "0.2"])
    assert short.returncode == 0
    short_out = short.stdout

    long = run_cli(["simulate", "--duration", "1.0"])
    assert long.returncode == 0
    long_out = long.stdout

    def extract_total(out):
        for line in out.splitlines():
            if "Total words captured" in line:
                return int(line.split(":")[1].strip())
        return 0

    assert extract_total(long_out) > extract_total(short_out)


def test_simulate_invalid_duration():
    result = run_cli(["simulate", "--duration", "-1"])
    assert result.returncode != 0


def test_replay_basic(tmp_path):
    log = tmp_path / "record.jsonl"
    log.write_text(
        json.dumps({
            "timestamp": time.time(),
            "word_int": 0x9c000c26,
            "parity_type": Word.ODD_PARITY,
            "source_id": "SRC"
        }) + "\n",
        encoding="utf-8"
    )

    result = run_cli(["replay", str(log), "--speed", "1.0"])
    assert result.returncode == 0

    out = result.stdout
    assert "Loading record file" in out
    assert "Starting playback" in out
    assert "Replay Summary" in out
    assert "Total words replayed/captured" in out
    assert "Replay session completed" in out


def test_replay_with_speed(tmp_path):
    log = tmp_path / "record.jsonl"
    log.write_text(
        json.dumps({
            "timestamp": time.time(),
            "word_int": 0x9c000c26,
            "parity_type": Word.ODD_PARITY,
            "source_id": "SRC"
        }) + "\n",
        encoding="utf-8"
    )

    result = run_cli(["replay", str(log), "--speed", "2.5"])
    assert result.returncode == 0

    out = result.stdout
    assert "Starting playback" in out
    assert "Replay session completed" in out


def test_replay_rejects_nonpositive_speed(tmp_path):
    log = tmp_path / "record.jsonl"
    log.write_text(
        json.dumps({
            "timestamp": time.time(),
            "word_int": 0x9c000c26,
            "parity_type": Word.ODD_PARITY,
            "source_id": "SRC"
        }) + "\n",
        encoding="utf-8"
    )

    result = run_cli(["replay", str(log), "--speed", "0"])
    assert result.returncode != 0
    assert "--speed must be positive" in result.stdout


def test_replay_file_not_found():
    result = run_cli(["replay", "no_such_file.jsonl"])
    assert result.returncode == 0

    out = result.stdout.lower()
    err = result.stderr.lower()

    assert "filenotfounderror" in err
    assert "record file not found" in err
    assert "replay summary" in out
    assert "replay session completed" in out


def test_generate_cli_success(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps({
            "labels": [
                {
                    "label": "0o203",
                    "name": "Pressure Altitude",
                    "system": "ADC",
                    "category": "Air Data",
                    "fields": [
                        {"name": "Altitude", "lsb": 11, "msb": 28, "type": "BNR", "resolution": 1.0, "unit": "ft"}
                    ],
                }
            ]
        }),
        encoding="utf-8",
    )

    out_file = tmp_path / "generated_icd.py"
    result = run_cli(["generate", str(icd_file), "--output", str(out_file)])
    
    assert result.returncode == 0
    assert out_file.exists()
    
    content = out_file.read_text(encoding="utf-8")
    assert "PressureAltitudeData" in content
    assert "ICD_REGISTRY" in content
    assert "decode_icd_word" in content


def test_generate_cli_stdout(tmp_path):
    icd_file = tmp_path / "icd.json"
    icd_file.write_text(
        json.dumps({
            "labels": [
                {
                    "label": 123,
                    "name": "Stdout Label",
                    "system": "SYS",
                    "category": "Cat"
                }
            ]
        }),
        encoding="utf-8",
    )

    result = run_cli(["generate", str(icd_file)])
    assert result.returncode == 0
    assert "StdoutLabelData" in result.stdout


def test_generate_cli_file_not_found():
    result = run_cli(["generate", "non_existent_icd.json"])
    assert result.returncode != 0
    assert "Error" in result.stderr or "Error" in result.stdout


def test_replay_rejects_nonpositive_speed(tmp_path):
    log = tmp_path / "record.jsonl"
    log.write_text(
        json.dumps({
            "timestamp": time.time(),
            "word_int": 0x9c000c26,
            "parity_type": Word.ODD_PARITY,
            "source_id": "SRC"
        }) + "\n",
        encoding="utf-8"
    )

    result = run_cli(["replay", str(log), "--speed", "0"])
    assert result.returncode != 0
    assert "--speed must be positive" in result.stdout
