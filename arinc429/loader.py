from __future__ import annotations

from .bitfields import DATA_BITS
from .word import Word


class Arinc615Packetizer:
    """
    Splits a binary file into ARINC 429 words according to ARINC 615 rules.
    This is a simplified model: real ARINC 615 includes sequence counters,
    checksums, and control labels.
    """

    CONTROL_LABEL_SOF = 0o352
    CONTROL_LABEL_DATA = 0o350
    CONTROL_LABEL_EOF = 0o351

    # Max payload length encodable in the 19-bit DATA field used by SOF.
    MAX_SOF_LENGTH = (1 << DATA_BITS.width) - 1

    def __init__(self, data: bytes) -> None:
        self.data = data

    def _chunk(self, size: int) -> list[bytes]:
        return [self.data[i : i + size] for i in range(0, len(self.data), size)]

    def to_words(self) -> list[Word]:
        if len(self.data) > self.MAX_SOF_LENGTH:
            raise ValueError(
                f"Payload of {len(self.data)} bytes exceeds the "
                f"{self.MAX_SOF_LENGTH}-byte limit encodable in the SOF length field"
            )

        words: list[Word] = []

        sof = Word()
        sof.label = self.CONTROL_LABEL_SOF
        sof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, len(self.data))
        words.append(sof)

        for block in self._chunk(2):
            w = Word()
            w.label = self.CONTROL_LABEL_DATA
            value = int.from_bytes(block.ljust(2, b"\x00"), "big")
            w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, value)
            words.append(w)

        eof = Word()
        eof.label = self.CONTROL_LABEL_EOF
        eof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 0)
        words.append(eof)

        return words

    @staticmethod
    def decode(words: list[Word]) -> bytes:
        """
        Reconstruct the original byte payload from a list of words produced
        by to_words().

        Only words labeled CONTROL_LABEL_DATA contribute bytes; any other
        label (including CONTROL_LABEL_SOF, CONTROL_LABEL_EOF, or an
        injected/corrupted word) is ignored when accumulating data, but a
        leading CONTROL_LABEL_SOF word -- if present -- is used to trim the
        result to its exact recorded length, rather than guessing via
        trailing-null removal.

        If no SOF word is present (e.g. a hand-built or legacy word list),
        falls back to stripping trailing null bytes, matching the original
        behavior. This fallback has the same known limitation as before:
        a payload that itself ends in null bytes will have those bytes
        stripped too when no SOF length is available to disambiguate.
        """
        length: int | None = None
        data = bytearray()

        for w in words:
            if w.label == Arinc615Packetizer.CONTROL_LABEL_SOF and length is None:
                length = w.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
            elif w.label == Arinc615Packetizer.CONTROL_LABEL_DATA:
                value = w.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
                data.extend(value.to_bytes(2, "big"))

        if length is not None:
            if length > len(data):
                raise ValueError(
                    f"Specified length ({length}) exceeds available decoded data length ({len(data)})"
                )
            return bytes(data[:length])
        return bytes(data).rstrip(b"\x00")
