import pytest

from arinc429 import DATA_BITS, Word
from arinc429.williamsburg import (
    DataBeforeSOF,
    EOFBeforeSOF,
    LengthMismatch,
    UnexpectedLabel,
    WilliamsburgReceiver,
    WilliamsburgTransmitter,
)


def extract_payload(words: list[Word], strict: bool = False) -> bytes | None:
    rx = WilliamsburgReceiver(strict=strict)
    result = None
    for w in words:
        out = rx.process_word(w)
        if out is not None:
            result = out
    return result


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"A",
        b"XYZ",
        b"HELLO",
        b"0123456789" * 50,
    ],
)
def test_roundtrip_payload(data: bytes):
    tx = WilliamsburgTransmitter()
    words = tx.encode(data)
    payload = extract_payload(words)
    assert payload == data


def test_first_and_last_labels():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"ABC")
    assert words[0].label == WilliamsburgTransmitter.LABEL_SOF
    assert words[-1].label == WilliamsburgTransmitter.LABEL_EOF


def test_data_words_have_correct_label():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"ABCDEFG")
    for w in words[1:-1]:
        assert w.label == WilliamsburgTransmitter.LABEL_DATA


def test_data_field_encoding_two_bytes():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"AB")
    w = words[1]
    value = w.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
    assert value.to_bytes(2, "big") == b"AB"


def test_padding_is_removed_lenient():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"XY")
    payload = extract_payload(words)
    assert payload.startswith(b"XY")


def test_receiver_returns_none_until_eof():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"TEST")
    rx = WilliamsburgReceiver()
    for w in words[:-1]:
        assert rx.process_word(w) is None
    assert rx.process_word(words[-1]) == b"TEST"


def test_zero_length_chunk_size_is_invalid():
    with pytest.raises(ValueError):
        WilliamsburgTransmitter(chunk_size=0)


def test_chunk_size_greater_than_two_is_invalid():
    with pytest.raises(ValueError):
        WilliamsburgTransmitter(chunk_size=3)


def test_receiver_ignores_words_before_sof_lenient():
    rx = WilliamsburgReceiver(strict=False)

    w = Word()
    w.label = 0o123
    assert rx.process_word(w) is None

    tx = WilliamsburgTransmitter()
    words = tx.encode(b"DATA")
    payload = None
    for w in words:
        out = rx.process_word(w)
        if out is not None:
            payload = out

    assert payload == b"DATA"


def test_receiver_handles_interrupted_sequence_lenient():
    rx = WilliamsburgReceiver(strict=False)
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"HELLO")

    assert rx.process_word(words[0]) is None
    assert rx.process_word(words[1]) is None

    bad = Word()
    bad.label = 0o123
    assert rx.process_word(bad) is None

    assert rx.process_word(words[-1]) is None


def test_receiver_multiple_frames_lenient():
    tx = WilliamsburgTransmitter()
    frame1 = tx.encode(b"AAA")
    frame2 = tx.encode(b"BBB")

    rx = WilliamsburgReceiver(strict=False)

    out1 = None
    out2 = None

    for w in frame1:
        r = rx.process_word(w)
        if r is not None:
            out1 = r

    for w in frame2:
        r = rx.process_word(w)
        if r is not None:
            out2 = r

    assert out1 == b"AAA"
    assert out2 == b"BBB"


def test_strict_data_before_sof_raises():
    rx = WilliamsburgReceiver(strict=True)
    w = Word()
    w.label = WilliamsburgReceiver.LABEL_DATA
    with pytest.raises(DataBeforeSOF):
        rx.process_word(w)


def test_strict_eof_before_sof_raises():
    rx = WilliamsburgReceiver(strict=True)
    w = Word()
    w.label = WilliamsburgReceiver.LABEL_EOF
    with pytest.raises(EOFBeforeSOF):
        rx.process_word(w)


def test_strict_unexpected_label_before_sof_raises():
    rx = WilliamsburgReceiver(strict=True)
    w = Word()
    w.label = 0o123
    with pytest.raises(UnexpectedLabel):
        rx.process_word(w)


def test_strict_unexpected_label_during_assembly_raises():
    rx = WilliamsburgReceiver(strict=True)
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"HELLO")

    assert rx.process_word(words[0]) is None
    assert rx.process_word(words[1]) is None

    bad = Word()
    bad.label = 0o123
    with pytest.raises(UnexpectedLabel):
        rx.process_word(bad)


def test_strict_length_mismatch_raises():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"ABC")

    rx = WilliamsburgReceiver(strict=True)

    # SOF
    assert rx.process_word(words[0]) is None

    # DATA: drop one data word to force length mismatch
    assert rx.process_word(words[1]) is None

    # EOF: expected_length > actual buffer length
    with pytest.raises(LengthMismatch):
        rx.process_word(words[-1])
