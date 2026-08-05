from __future__ import annotations

import pytest

from arinc429 import DATA_BITS, Word
from arinc429.williamsburg import (
    NakReason,
    WilliamsburgControlCode,
    WilliamsburgError,
    WilliamsburgSession,
    WilliamsburgState,
    crc16_ccitt,
)


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
    tx_session = WilliamsburgSession(is_transmitter=True)
    rx_session = WilliamsburgSession(is_transmitter=False)

    sal_words = tx_session.initiate_transfer(data)
    rts_words = rx_session.process_incoming_word(sal_words[0])
    assert rts_words is not None

    transfer_words = tx_session.process_incoming_word(rts_words[0])
    assert transfer_words is not None

    ack_words = None
    for w in transfer_words:
        res = rx_session.process_incoming_word(w)
        if res is not None:
            ack_words = res

    if ack_words:
        tx_session.process_incoming_word(ack_words[0])

    assert rx_session.get_received_data() == data


def test_data_field_encoding_two_bytes():
    tx_session = WilliamsburgSession(is_transmitter=True)
    chunks = tx_session._encode_payload_chunks(b"AB")
    value = chunks[0].get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
    assert value.to_bytes(2, "big") == b"AB"


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
    assert transfer is not None

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
    assert transfer is not None

    # Feed extra data words before EOF to simulate overflow / length mismatch
    extra_word = Word()
    extra_word.label = WilliamsburgSession.LABEL_DATA
    extra_word.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0x1234)

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


def test_session_payload_at_16bit_limit_roundtrips():
    """Payloads up to 0xFFFF bytes must transfer cleanly (length field is
    16-bit); the old 19-bit limit silently truncated larger lengths."""
    tx_session = WilliamsburgSession(is_transmitter=True)
    rx_session = WilliamsburgSession(is_transmitter=False)

    payload = bytes(range(256)) * 255  # 65280 bytes, fits in 16 bits
    assert len(payload) <= 0xFFFF

    sal = tx_session.initiate_transfer(payload)
    rts = rx_session.process_incoming_word(sal[0])
    assert rts is not None
    transfer = tx_session.process_incoming_word(rts[0])
    assert transfer is not None

    ack = None
    for w in transfer:
        res = rx_session.process_incoming_word(w)
        if res is not None:
            ack = res
    assert ack is not None
    assert rx_session.get_received_data() == payload


def test_session_payload_over_16bit_limit_raises():
    """65536 bytes cannot fit in the 16-bit length/param field and must be
    rejected up front instead of silently corrupting the transfer."""
    tx_session = WilliamsburgSession(is_transmitter=True)
    with pytest.raises(ValueError, match="16-bit"):
        tx_session.initiate_transfer(b"\x00" * (0xFFFF + 1))
