import pytest

from arinc429.arinc429 import DATA_BITS, Word
from arinc429.williamsburg import WilliamsburgReceiver, WilliamsburgTransmitter


def extract_payload(words: list[Word]) -> bytes:
    """Utility: feed words into a receiver and return the decoded payload."""
    rx = WilliamsburgReceiver()
    result = None
    for w in words:
        out = rx.process_word(w)
        if out is not None:
            result = out
    return result


def test_empty_payload():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"")
    payload = extract_payload(words)
    assert payload == b""


def test_single_byte():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"A")
    payload = extract_payload(words)
    assert payload.startswith(b"A")


def test_three_bytes_exact():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"XYZ")
    payload = extract_payload(words)
    assert payload.startswith(b"XYZ")


def test_non_aligned_payload():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"HELLO")
    payload = extract_payload(words)
    assert payload.startswith(b"HELLO")


def test_large_payload():
    data = b"0123456789" * 50  # 500 bytes
    tx = WilliamsburgTransmitter()
    words = tx.encode(data)
    payload = extract_payload(words)
    assert payload == data


def test_first_word_is_sof():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"ABC")
    assert words[0].label == WilliamsburgTransmitter.LABEL_SOF


def test_last_word_is_eof():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"ABC")
    assert words[-1].label == WilliamsburgTransmitter.LABEL_EOF


def test_data_words_have_correct_label():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"ABCDEFG")
    # Skip SOF and EOF
    for w in words[1:-1]:
        assert w.label == WilliamsburgTransmitter.LABEL_DATA


def test_data_field_encoding():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"AB")  # 2 bytes

    w = words[1]
    value = w.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
    assert value.to_bytes(2, "big") == b"AB"


def test_receiver_ignores_words_before_sof():
    rx = WilliamsburgReceiver()

    # Random word before SOF
    w = Word()
    w.label = 0o123
    assert rx.process_word(w) is None

    # Now send a valid frame
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"DATA")
    payload = None
    for w in words:
        out = rx.process_word(w)
        if out is not None:
            payload = out

    assert payload == b"DATA"


def test_receiver_handles_interrupted_sequence():
    rx = WilliamsburgReceiver()

    tx = WilliamsburgTransmitter()
    words = tx.encode(b"HELLO")

    # Feed SOF + first data word
    assert rx.process_word(words[0]) is None
    assert rx.process_word(words[1]) is None

    # Inject a wrong label (breaks sequence)
    bad = Word()
    bad.label = 0o123
    assert rx.process_word(bad) is None

    # Feed EOF — should NOT complete because sequence was broken
    assert rx.process_word(words[-1]) is None


def test_receiver_multiple_frames():
    tx = WilliamsburgTransmitter()

    frame1 = tx.encode(b"AAA")
    frame2 = tx.encode(b"BBB")

    rx = WilliamsburgReceiver()

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

    assert out1.startswith(b"AAA")
    assert out2.startswith(b"BBB")


def test_zero_length_chunk_size_is_invalid():
    with pytest.raises(ValueError):
        WilliamsburgTransmitter(chunk_size=0)


def test_chunk_size_larger_than_payload():
    with pytest.raises(ValueError):
        WilliamsburgTransmitter(chunk_size=100)


def test_padding_is_removed():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"XY")  # 2 bytes → padded to 3
    payload = extract_payload(words)
    assert payload.startswith(b"XY")


def test_receiver_returns_none_until_eof():
    tx = WilliamsburgTransmitter()
    words = tx.encode(b"TEST")

    rx = WilliamsburgReceiver()
    for w in words[:-1]:
        assert rx.process_word(w) is None

    assert rx.process_word(words[-1]) == b"TEST"
