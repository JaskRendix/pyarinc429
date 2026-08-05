import pytest

from arinc429 import DATA_BITS, Word
from arinc429.williamsburg import (
    DataBeforeSOF,
    EOFBeforeSOF,
    LengthMismatch,
    NakReason,
    UnexpectedLabel,
    WilliamsburgControlCode,
    WilliamsburgError,
    WilliamsburgReceiver,
    WilliamsburgSession,
    WilliamsburgState,
    WilliamsburgTransmitter,
    crc16_ccitt,
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
        b"0123456789" * 5,
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


def test_session_stateful_roundtrip():
    tx_session = WilliamsburgSession(is_transmitter=True)
    rx_session = WilliamsburgSession(is_transmitter=False)

    payload = b"WILLSBURG PROTOCOL TEST"

    # 1. Transmitter initiates transfer -> SAL word
    sal_words = tx_session.initiate_transfer(payload)
    assert len(sal_words) == 1
    assert tx_session.state == WilliamsburgState.WAIT_RTS

    # 2. Receiver processes SAL -> returns RTS
    rts_words = rx_session.process_incoming_word(sal_words[0])
    assert rts_words is not None
    assert len(rts_words) == 1
    assert rx_session.state == WilliamsburgState.SENT_RTS

    # 3. Transmitter processes RTS -> returns CTS, SOF, DATA..., EOF
    transfer_words = tx_session.process_incoming_word(rts_words[0])
    assert transfer_words is not None
    assert tx_session.state == WilliamsburgState.WAIT_ACK

    # 4. Receiver processes transfer sequence (CTS, SOF, DATA, EOF) -> returns ACK
    ack_words = None
    for w in transfer_words:
        res = rx_session.process_incoming_word(w)
        if res is not None:
            ack_words = res

    assert ack_words is not None
    assert len(ack_words) == 1
    assert rx_session.state == WilliamsburgState.IDLE
    assert rx_session.get_received_data() == payload

    # 5. Transmitter processes ACK -> returns to IDLE
    final_res = tx_session.process_incoming_word(ack_words[0])
    assert final_res is None
    assert tx_session.state == WilliamsburgState.IDLE


def test_session_init_receiver_raises():
    rx_session = WilliamsburgSession(is_transmitter=False)
    with pytest.raises(RuntimeError):
        rx_session.initiate_transfer(b"data")


def test_session_init_busy_raises():
    tx_session = WilliamsburgSession(is_transmitter=True)
    tx_session.initiate_transfer(b"first")
    with pytest.raises(RuntimeError):
        tx_session.initiate_transfer(b"second")


def test_session_payload_too_large_raises():
    tx_session = WilliamsburgSession(is_transmitter=True)
    huge_payload = b"\x00" * (1 << 20)
    with pytest.raises(ValueError):
        tx_session.initiate_transfer(huge_payload)


def test_session_crc_mismatch_triggers_nak():
    tx_session = WilliamsburgSession(is_transmitter=True)
    rx_session = WilliamsburgSession(is_transmitter=False)

    payload = b"CORRECT DATA"
    sal = tx_session.initiate_transfer(payload)
    rts = rx_session.process_incoming_word(sal[0])
    transfer = tx_session.process_incoming_word(rts[0])

    # Tamper with a data word in the stream
    for w in transfer:
        if w.label == WilliamsburgSession.LABEL_DATA:
            w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0xFFFF)
            break

    nak_words = None
    for w in transfer:
        res = rx_session.process_incoming_word(w)
        if res is not None:
            nak_words = res

    assert nak_words is not None
    assert rx_session.state == WilliamsburgState.ERROR

    # Transmitter processes NAK -> raises WilliamsburgError
    with pytest.raises(WilliamsburgError):
        tx_session.process_incoming_word(nak_words[0])
    assert tx_session.state == WilliamsburgState.ERROR


def test_session_buffer_overflow_triggers_nak():
    tx_session = WilliamsburgSession(is_transmitter=True)
    rx_session = WilliamsburgSession(is_transmitter=False)

    payload = b"SHORT"
    sal = tx_session.initiate_transfer(payload)
    rts = rx_session.process_incoming_word(sal[0])
    transfer = tx_session.process_incoming_word(rts[0])

    # Feed extra data words before EOF to simulate overflow / length mismatch
    extra_word = Word()
    extra_word.label = WilliamsburgSession.LABEL_DATA
    extra_word.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0x1234)

    nak_words = None
    for w in transfer[:-1]:  # Feed everything up to EOF
        rx_session.process_incoming_word(w)

    rx_session.process_incoming_word(extra_word)  # Inject extra data
    nak_words = rx_session.process_incoming_word(transfer[-1])  # Process EOF

    assert nak_words is not None
    code, param = rx_session._parse_control_word(nak_words[0])
    assert code == WilliamsburgControlCode.NAK
    assert param == NakReason.BUFFER_OVERFLOW


def test_session_reset():
    session = WilliamsburgSession(is_transmitter=True)
    session.state = WilliamsburgState.ERROR
    session.payload = b"test"
    session.reset()
    assert session.state == WilliamsburgState.IDLE
    assert session.payload == b""
    assert len(session.rx_buffer) == 0
