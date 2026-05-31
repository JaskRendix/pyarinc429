from __future__ import annotations

from collections.abc import Iterable

from .arinc429 import DATA_BITS, Word


class WilliamsburgReceiver:
    """
    Reassembles multi-word Williamsburg block transfers.
    """

    LABEL_SOF = 0o144
    LABEL_EOF = 0o145
    LABEL_DATA = 0o146

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.assembling = False

    def process_word(self, word: Word) -> bytes | None:
        """
        Process a single ARINC 429 word.
        Returns a completed block when EOF is received.
        """

        if word.label == self.LABEL_SOF:
            self.buffer.clear()
            self.assembling = True
            return None

        if not self.assembling:
            return None

        if word.label == self.LABEL_DATA:
            value = word.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
            self.buffer.extend(value.to_bytes(2, "big"))
            return None

        if word.label == self.LABEL_EOF:
            self.assembling = False
            return bytes(self.buffer)

        # Unexpected label → abort frame
        self.buffer.clear()
        self.assembling = False
        return None


class WilliamsburgTransmitter:
    """
    Splits a byte stream into Williamsburg block-transfer ARINC 429 words.

    Produces:
        SOF → DATA... → EOF
    """

    LABEL_SOF = 0o144
    LABEL_EOF = 0o145
    LABEL_DATA = 0o146

    def __init__(self, chunk_size: int = 2) -> None:
        """
        chunk_size: number of bytes per ARINC 429 data word.
                    2 bytes = 16 bits → fits inside DATA_BITS (19 bits).
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_size > 2:
            raise ValueError("chunk_size must be <= 2 for 19-bit DATA field")
        self.chunk_size = chunk_size

    def _chunk(self, data: bytes) -> Iterable[bytes]:
        for i in range(0, len(data), self.chunk_size):
            yield data[i : i + self.chunk_size]

    def encode(self, data: bytes) -> list[Word]:
        """
        Convert a byte sequence into Williamsburg ARINC 429 words.
        """

        words: list[Word] = []

        # Start-of-frame
        sof = Word()
        sof.label = self.LABEL_SOF
        sof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0)
        words.append(sof)

        # Data blocks
        for block in self._chunk(data):
            w = Word()
            w.label = self.LABEL_DATA
            value = int.from_bytes(block.ljust(2, b"\x00"), "big")
            w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, value)
            words.append(w)

        # End-of-frame
        eof = Word()
        eof.label = self.LABEL_EOF
        eof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0)
        words.append(eof)

        return words
