import subprocess
import json
import pytest
from pathlib import Path


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
    # argparse uses exit code 2 for missing command
    assert result.returncode == 2


def test_unknown_command():
    result = run_cli(["no_such_command"])
    assert result.returncode != 0
    assert "invalid choice" in result.stdout.lower() or "usage" in result.stdout.lower()


def test_help():
    result = run_cli(["--help"])
    assert result.returncode == 0

    out = result.stdout
    assert "decode" in out
    assert "arinc615-encode" in out
    assert "williamsburg-simulate" in out

