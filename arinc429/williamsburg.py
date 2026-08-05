from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum, auto

from .bitfields import DATA_BITS
from .word import Word

# 19-bit max integer limit for ARINC 429 DATA field (bits 11..29)
MAX_PAYLOAD_BYTES = (1 << (DATA_BITS.msb - DATA_BITS.lsb + 1)) - 1


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    """
    Computes CRC-16-CCITT (polynomial 0x1021) over a byte payload.
    Used for ARINC block transfer integrity verification.
    """
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


class WilliamsburgState(Enum):
    """Protocol state machine states."""

    IDLE = auto()
    WAIT_RTS = auto()
    SENDING_BLOCK = auto()
    WAIT_ACK = auto()
    SENT_RTS = auto()
    RECEIVING = auto()
    ERROR = auto()


class WilliamsburgControlCode(Enum):
    """Sub-label control codes packed into control word parameters."""

    SAL = 0x01
    RTS = 0x02
    CTS = 0x03
    SOF = 0x04
    EOF = 0x05
    ACK = 0x06
    NAK = 0x07


class NakReason(IntEnum):
    """Error codes carried in NAK control words."""

    NONE = 0x00
    CHECKSUM_MISMATCH = 0x01
    SEQUENCE_ERROR = 0x02
    BUFFER_OVERFLOW = 0x03
    TIMEOUT = 0x04


class WilliamsburgError(Exception):
    """Base exception for Williamsburg protocol errors."""

    pass


class UnexpectedLabel(WilliamsburgError):
    pass


class DataBeforeSOF(WilliamsburgError):
    pass


class EOFBeforeSOF(WilliamsburgError):
    pass


class LengthMismatch(WilliamsburgError):
    pass


@dataclass
class WilliamsburgSession:
    """
    ARINC 429 Williamsburg Protocol Engine with CRC-16 Integrity Check.

    Handles both transmitter and receiver roles via state transitions driven
    by `process_incoming_word()`.
    """

    dest_address: int = 0
    src_address: int = 0
    is_transmitter: bool = True

    LABEL_CONTROL: int = 0o144  # Control word label (SAL/RTS/CTS/SOF/EOF/ACK/NAK)
    LABEL_DATA: int = 0o146     # Data word label

    def __post_init__(self) -> None:
        self.state = WilliamsburgState.IDLE
        self.payload = b""
        self.rx_buffer = bytearray()
        self.expected_length = 0

    def reset(self) -> None:
        """Reset the session to IDLE state and clear internal buffers."""
        self.state = WilliamsburgState.IDLE
        self.payload = b""
        self.rx_buffer.clear()
        self.expected_length = 0

    def initiate_transfer(self, payload: bytes) -> list[Word]:
        """
        Initiates a Williamsburg transfer sequence (Transmitter side).

        Returns the initial SAL control word to be sent on the bus.
        """
        if not self.is_transmitter:
            raise RuntimeError("Cannot initiate transfer on a receiver-configured session")

        if self.state != WilliamsburgState.IDLE:
            raise RuntimeError(f"Cannot start transfer: session in state {self.state}")

        if len(payload) > MAX_PAYLOAD_BYTES:
            raise ValueError(
                f"Payload size ({len(payload)} bytes) exceeds maximum allowable 19-bit limit ({MAX_PAYLOAD_BYTES} bytes)"
            )

        self.payload = payload
        self.state = WilliamsburgState.WAIT_RTS

        # Build and return initial SAL word
        sal_word = self._build_control_word(
            code=WilliamsburgControlCode.SAL,
            param=len(payload),
        )
        return [sal_word]

    def process_incoming_word(self, word: Word) -> list[Word] | None:
        """
        Process an incoming ARINC 429 word and advance the FSM state.

        Returns:
            list[Word]: Words to transmit back on the bus, or None if no response is required.
        """
        # Non-control word handling
        if word.label != self.LABEL_CONTROL:
            if self.state == WilliamsburgState.RECEIVING and word.label == self.LABEL_DATA:
                # Accumulate raw payload bits (2 bytes per word)
                val = word.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
                self.rx_buffer.extend(val.to_bytes(2, "big"))
            return None

        control_code, param = self._parse_control_word(word)

        if not self.is_transmitter:
            if self.state == WilliamsburgState.IDLE and control_code == WilliamsburgControlCode.SAL:
                self.expected_length = param
                self.rx_buffer.clear()
                self.state = WilliamsburgState.SENT_RTS
                return [self._build_control_word(WilliamsburgControlCode.RTS, param)]

            elif self.state == WilliamsburgState.SENT_RTS and control_code == WilliamsburgControlCode.SOF:
                self.state = WilliamsburgState.RECEIVING
                return None

            elif self.state == WilliamsburgState.RECEIVING and control_code == WilliamsburgControlCode.EOF:
                # EOF received: Verify payload length and CRC-16
                received_crc = param
                actual_payload = bytes(self.rx_buffer[: self.expected_length])

                # 1. Length Check
                if len(self.rx_buffer) < self.expected_length:
                    self.state = WilliamsburgState.ERROR
                    return [
                        self._build_control_word(
                            WilliamsburgControlCode.NAK,
                            NakReason.BUFFER_OVERFLOW,
                        )
                    ]

                # 2. CRC-16 Integrity Check
                computed_crc = crc16_ccitt(actual_payload)
                if computed_crc != received_crc:
                    self.state = WilliamsburgState.ERROR
                    return [
                        self._build_control_word(
                            WilliamsburgControlCode.NAK,
                            NakReason.CHECKSUM_MISMATCH,
                        )
                    ]

                # Validation Passed -> Acknowledge transfer and return to IDLE
                self.state = WilliamsburgState.IDLE
                return [self._build_control_word(WilliamsburgControlCode.ACK, 0)]
        else:
            if self.state == WilliamsburgState.WAIT_RTS and control_code == WilliamsburgControlCode.RTS:
                self.state = WilliamsburgState.SENDING_BLOCK

                # Calculate payload CRC-16 before streaming
                payload_crc = crc16_ccitt(self.payload)

                words = [
                    self._build_control_word(WilliamsburgControlCode.CTS, len(self.payload)),
                    self._build_control_word(WilliamsburgControlCode.SOF, len(self.payload)),
                ]

                # Append DATA payload words
                words.extend(self._encode_payload_chunks(self.payload))

                # Append EOF carrying payload CRC-16 in parameter field
                words.append(
                    self._build_control_word(WilliamsburgControlCode.EOF, payload_crc)
                )

                self.state = WilliamsburgState.WAIT_ACK
                return words

            elif self.state == WilliamsburgState.WAIT_ACK:
                if control_code == WilliamsburgControlCode.ACK:
                    self.state = WilliamsburgState.IDLE
                    return None

                elif control_code == WilliamsburgControlCode.NAK:
                    reason = (
                        NakReason(param)
                        if param in NakReason._value2member_map_
                        else param
                    )
                    self.state = WilliamsburgState.ERROR
                    raise WilliamsburgError(
                        f"Transmission rejected by receiver with NAK (Reason: {reason})"
                    )

        return None

    def get_received_data(self) -> bytes | None:
        """
        Returns the reconstructed payload if a transfer completed successfully.
        """
        if not self.is_transmitter and self.state == WilliamsburgState.IDLE and self.rx_buffer:
            return bytes(self.rx_buffer[: self.expected_length])
        return None

   def _build_control_word(self, code: WilliamsburgControlCode, param: int) -> Word:
        """
        Packs [4-bit Code | 16-bit Parameter/CRC] into 19-bit DATA field (bits 11-29).
        """
        w = Word()
        w.label = self.LABEL_CONTROL
        packed_val = ((code.value & 0xF) << 15) | (param & 0xFFFF)
        w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, packed_val)
        return w

    def _parse_control_word(self, word: Word) -> tuple[WilliamsburgControlCode, int]:
        raw_val = word.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
        code_val = (raw_val >> 15) & 0xF
        param = raw_val & 0xFFFF

        try:
            code = WilliamsburgControlCode(code_val)
        except ValueError:
            raise UnexpectedLabel(f"Unknown control code {code_val}")

        return code, param

    def _encode_payload_chunks(self, data: bytes) -> list[Word]:
        words = []
        for i in range(0, len(data), 2):
            chunk = data[i: i + 2].ljust(2, b"\x00")
            w = Word()
            w.label = self.LABEL_DATA
            w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, int.from_bytes(chunk, "big"))
            words.append(w)
        return words
