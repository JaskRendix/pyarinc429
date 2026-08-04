from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .bitfields import DATA_BITS
from .word import Word


class WilliamsburgError(Exception):
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
class WilliamsburgReceiver:
    """
    Reassembles multi-word Williamsburg block transfers.
    """

    strict: bool = False
    pad_byte: int = 0x00

    LABEL_SOF: int = 0o144
    LABEL_EOF: int = 0o145
    LABEL_DATA: int = 0o146

    def __post_init__(self) -> None:
        self.buffer = bytearray()
        self.assembling = False
        self.expected_length: int | None = None

    def _error(self, exc: Exception) -> None:
        if self.strict:
            raise exc
        # lenient mode: abort silently
        self.buffer.clear()
        self.assembling = False
        self.expected_length = None

    def process_word(self, word: Word) -> bytes | None:
        """
        Process a single ARINC 429 word.
        Returns a completed block when EOF is received.
        """

        label = word.label

        if label == self.LABEL_SOF:
            self.buffer.clear()
            self.assembling = True
            self.expected_length = word.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
            return None

        if not self.assembling:
            if label == self.LABEL_DATA:
                self._error(DataBeforeSOF())
            elif label == self.LABEL_EOF:
                self._error(EOFBeforeSOF())
            else:
                self._error(UnexpectedLabel(label))
            return None

        if label == self.LABEL_DATA:
            value = word.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
            self.buffer.extend(value.to_bytes(2, "big"))
            return None

        if label == self.LABEL_EOF:
            self.assembling = False

            if self.expected_length is None:
                return bytes(self.buffer)

            if self.strict and len(self.buffer) < self.expected_length:
                raise LengthMismatch(
                    f"Expected {self.expected_length} bytes, got {len(self.buffer)}"
                )

            return bytes(self.buffer[: self.expected_length])

        self._error(UnexpectedLabel(label))
        return None


@dataclass
class WilliamsburgTransmitter:
    """
    Splits a byte stream into Williamsburg block-transfer ARINC 429 words.
    """

    chunk_size: int = 2
    pad_byte: int = 0x00

    LABEL_SOF: int = 0o144
    LABEL_EOF: int = 0o145
    LABEL_DATA: int = 0o146

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if self.chunk_size > 2:
            raise ValueError("chunk_size must be <= 2 for 19-bit DATA field")

    def _chunk(self, data: bytes) -> Iterable[bytes]:
        for i in range(0, len(data), self.chunk_size):
            yield data[i : i + self.chunk_size]

    def encode(self, data: bytes) -> list[Word]:
        """
        Convert a byte sequence into Williamsburg ARINC 429 words.
        """

        words: list[Word] = []

        # SOF
        sof = Word()
        sof.label = self.LABEL_SOF
        sof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, len(data))
        words.append(sof)

        # DATA
        for block in self._chunk(data):
            w = Word()
            w.label = self.LABEL_DATA
            padded = block.ljust(2, bytes([self.pad_byte]))
            value = int.from_bytes(padded, "big")
            w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, value)
            words.append(w)

        # EOF
        eof = Word()
        eof.label = self.LABEL_EOF
        eof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0)
        words.append(eof)

        return words
