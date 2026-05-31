from arinc429.arinc429 import DATA_BITS, Word
from arinc429.loader import Arinc615Packetizer


def decode_packetizer_words(words: list[Word]) -> bytes:
    """Reconstruct payload from packetizer output."""
    data = bytearray()
    for w in words:
        if w.label == Arinc615Packetizer.CONTROL_LABEL_DATA:
            value = w.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
            data.extend(value.to_bytes(2, "big"))
    return bytes(data).rstrip(b"\x00")


def test_empty_payload():
    p = Arinc615Packetizer(b"")
    words = p.to_words()

    # Should produce only EOF
    assert len(words) == 1
    assert words[0].label == Arinc615Packetizer.CONTROL_LABEL_EOF

    # Reconstructed payload is empty
    assert decode_packetizer_words(words) == b""


def test_single_byte():
    p = Arinc615Packetizer(b"A")
    words = p.to_words()
    assert decode_packetizer_words(words) == b"A"


def test_three_bytes_exact():
    p = Arinc615Packetizer(b"XYZ")
    words = p.to_words()
    assert decode_packetizer_words(words) == b"XYZ"


def test_non_aligned_payload():
    p = Arinc615Packetizer(b"HELLO")
    words = p.to_words()
    assert decode_packetizer_words(words) == b"HELLO"


def test_large_payload():
    data = b"0123456789" * 100  # 1000 bytes
    p = Arinc615Packetizer(data)
    words = p.to_words()
    assert decode_packetizer_words(words) == data


def test_all_data_words_have_correct_label():
    p = Arinc615Packetizer(b"ABCDEFGH")
    words = p.to_words()

    # All except last must be DATA
    for w in words[:-1]:
        assert w.label == Arinc615Packetizer.CONTROL_LABEL_DATA

    # Last must be EOF
    assert words[-1].label == Arinc615Packetizer.CONTROL_LABEL_EOF


def test_eof_word_has_zero_data_field():
    p = Arinc615Packetizer(b"ABC")
    words = p.to_words()
    eof = words[-1]
    assert eof.label == Arinc615Packetizer.CONTROL_LABEL_EOF
    assert eof.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb) == 0


def test_data_field_encoding():
    p = Arinc615Packetizer(b"ABCDEF")
    words = p.to_words()

    # First block = b"ABC"
    w = words[0]
    value = w.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
    assert value.to_bytes(2, "big") == b"AB"


def test_padding_is_removed_on_decode():
    p = Arinc615Packetizer(b"XY")  # 2 bytes → padded to 3
    words = p.to_words()
    assert decode_packetizer_words(words) == b"XY"


def test_multiple_blocks_padding():
    p = Arinc615Packetizer(b"ABCDE")  # 5 bytes → blocks: ABC, DE + pad
    words = p.to_words()
    assert decode_packetizer_words(words) == b"ABCDE"


def test_packetizer_does_not_mutate_input():
    data = b"HELLO"
    p = Arinc615Packetizer(data)
    _ = p.to_words()
    assert data == b"HELLO"


def test_corrupted_label_does_not_break_decode():
    p = Arinc615Packetizer(b"DATA")
    words = p.to_words()

    # Corrupt one data word
    corrupted = words.copy()
    corrupted[1] = Word()  # label defaults to 0o0

    # decode should ignore corrupted word and still return partial data
    decoded = decode_packetizer_words(corrupted)
    assert decoded.startswith(b"D")  # first block intact


def test_manual_word_injection_before_eof():
    p = Arinc615Packetizer(b"ABC")
    words = p.to_words()

    # Inject a random word before EOF
    w = Word()
    w.label = 0o123
    corrupted = words[:-1] + [w] + [words[-1]]

    decoded = decode_packetizer_words(corrupted)
    assert decoded == b"ABC"


def test_round_trip_consistency_small():
    data = b"TEST123"
    p = Arinc615Packetizer(data)
    words = p.to_words()
    assert decode_packetizer_words(words) == data


def test_round_trip_consistency_large():
    data = b"ABCDEFGH" * 200
    p = Arinc615Packetizer(data)
    words = p.to_words()
    assert decode_packetizer_words(words) == data
