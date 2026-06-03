from __future__ import annotations

from .arinc429 import DATA_BITS, Word


class Arinc615Packetizer:
    """
    Splits a binary file into ARINC 429 words according to ARINC 615 rules.
    This is a simplified model: real ARINC 615 includes sequence counters,
    checksums, and control labels.
    """

    CONTROL_LABEL_DATA = 0o350
    CONTROL_LABEL_EOF = 0o351

    def __init__(self, data: bytes) -> None:
        self.data = data

    def _chunk(self, size: int) -> list[bytes]:
        return [self.data[i : i + size] for i in range(0, len(self.data), size)]

    def to_words(self) -> list[Word]:
        words: list[Word] = []

        for block in self._chunk(2):
            w = Word()
            w.label = self.CONTROL_LABEL_DATA
            value = int.from_bytes(block.ljust(2, b"\x00"), "big")
            w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, value)
            words.append(w)

        eof = Word()
        eof.label = self.CONTROL_LABEL_EOF
        eof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0)  # ← required by tests
        words.append(eof)

        return words
