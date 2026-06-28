from arinc429.arinc429 import DATA_BITS, Word
from arinc429.loader import Arinc615Packetizer


def test_empty_payload():
    p = Arinc615Packetizer(b"")
    words = p.to_words()

    # Should produce only SOF + EOF, no DATA words
    assert len(words) == 2
    assert words[0].label == Arinc615Packetizer.CONTROL_LABEL_SOF
    assert words[-1].label == Arinc615Packetizer.CONTROL_LABEL_EOF

    # Reconstructed payload is empty
    assert Arinc615Packetizer.decode(words) == b""


def test_single_byte():
    p = Arinc615Packetizer(b"A")
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == b"A"


def test_three_bytes_exact():
    p = Arinc615Packetizer(b"XYZ")
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == b"XYZ"


def test_non_aligned_payload():
    p = Arinc615Packetizer(b"HELLO")
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == b"HELLO"


def test_large_payload():
    data = b"0123456789" * 100  # 1000 bytes
    p = Arinc615Packetizer(data)
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == data


def test_first_word_is_sof():
    p = Arinc615Packetizer(b"ABCDEFGH")
    words = p.to_words()
    assert words[0].label == Arinc615Packetizer.CONTROL_LABEL_SOF


def test_middle_words_are_data_last_is_eof():
    p = Arinc615Packetizer(b"ABCDEFGH")
    words = p.to_words()

    # Everything except the first (SOF) and last (EOF) must be DATA
    for w in words[1:-1]:
        assert w.label == Arinc615Packetizer.CONTROL_LABEL_DATA

    assert words[-1].label == Arinc615Packetizer.CONTROL_LABEL_EOF


def test_eof_word_has_zero_data_field():
    p = Arinc615Packetizer(b"ABC")
    words = p.to_words()
    eof = words[-1]
    assert eof.label == Arinc615Packetizer.CONTROL_LABEL_EOF
    assert eof.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb) == 0


def test_sof_word_carries_exact_payload_length():
    p = Arinc615Packetizer(b"ABCDEF")
    words = p.to_words()
    sof = words[0]
    assert sof.label == Arinc615Packetizer.CONTROL_LABEL_SOF
    assert sof.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb) == 6


def test_sof_word_length_zero_for_empty_payload():
    p = Arinc615Packetizer(b"")
    words = p.to_words()
    sof = words[0]
    assert sof.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb) == 0


def test_data_field_encoding():
    p = Arinc615Packetizer(b"ABCDEF")
    words = p.to_words()

    # First DATA block (index 1, since index 0 is SOF) = b"AB"
    w = words[1]
    assert w.label == Arinc615Packetizer.CONTROL_LABEL_DATA
    value = w.get_bit_field(DATA_BITS.lsb, DATA_BITS.msb)
    assert value.to_bytes(2, "big") == b"AB"


def test_padding_is_removed_on_decode():
    p = Arinc615Packetizer(b"XY")  # 2 bytes → padded to 3
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == b"XY"


def test_multiple_blocks_padding():
    p = Arinc615Packetizer(b"ABCDE")  # 5 bytes → blocks: ABC, DE + pad
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == b"ABCDE"


def test_packetizer_does_not_mutate_input():
    data = b"HELLO"
    p = Arinc615Packetizer(data)
    _ = p.to_words()
    assert data == b"HELLO"


def test_corrupted_data_word_does_not_break_decode():
    p = Arinc615Packetizer(b"DATA")
    words = p.to_words()

    # Corrupt the first DATA word (index 1; index 0 is SOF).
    # b"DATA" -> DATA words carry b"DA" then b"TA"; zeroing the first
    # leaves only b"TA" actually accumulated. SOF still claims length 4,
    # but decode() only trims to at most `length`, it never pads -- so
    # the corrupted word's bytes are simply absent from the result.
    corrupted = words.copy()
    corrupted[1] = Word()  # label defaults to 0o0

    decoded = Arinc615Packetizer.decode(corrupted)
    assert decoded == b"TA"


def test_manual_word_injection_before_eof():
    p = Arinc615Packetizer(b"ABC")
    words = p.to_words()

    # Inject a random word before EOF
    w = Word()
    w.label = 0o123
    corrupted = words[:-1] + [w] + [words[-1]]

    decoded = Arinc615Packetizer.decode(corrupted)
    assert decoded == b"ABC"


def test_round_trip_consistency_small():
    data = b"TEST123"
    p = Arinc615Packetizer(data)
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == data


def test_round_trip_consistency_large():
    data = b"ABCDEFGH" * 200
    p = Arinc615Packetizer(data)
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == data


def test_decode_is_callable_on_instance_too():
    p = Arinc615Packetizer(b"ABC")
    words = p.to_words()
    assert p.decode(words) == b"ABC"


def test_decode_uses_sof_length_not_null_stripping():
    # A payload that itself ends in a null byte must round-trip exactly
    # when SOF is present, unlike the old trailing-null-strip fallback.
    data = b"AB\x00"
    p = Arinc615Packetizer(data)
    words = p.to_words()
    assert Arinc615Packetizer.decode(words) == data


def test_decode_falls_back_to_null_strip_without_sof():
    # No SOF word present (hand-built list): falls back to the original
    # trailing-null-strip behavior, including its known limitation.
    w = Word()
    w.label = Arinc615Packetizer.CONTROL_LABEL_DATA
    w.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, int.from_bytes(b"AB", "big"))
    assert Arinc615Packetizer.decode([w]) == b"AB"


def test_decode_empty_word_list():
    assert Arinc615Packetizer.decode([]) == b""


def test_decode_with_only_eof_word():
    eof = Word()
    eof.label = Arinc615Packetizer.CONTROL_LABEL_EOF
    assert Arinc615Packetizer.decode([eof]) == b""


def test_decode_ignores_duplicate_sof_word():
    # Only the first SOF word's length is honored; a later duplicate
    # (e.g. injected or corrupted) must not override it.
    p = Arinc615Packetizer(b"ABCD")
    words = p.to_words()

    bogus_sof = Word()
    bogus_sof.label = Arinc615Packetizer.CONTROL_LABEL_SOF
    bogus_sof.set_bit_field(DATA_BITS.lsb, DATA_BITS.msb, 1)

    corrupted = [words[0]] + [bogus_sof] + words[1:]
    assert Arinc615Packetizer.decode(corrupted) == b"ABCD"


def test_to_words_raises_on_payload_exceeding_sof_length_limit():
    too_big = b"\x00" * (Arinc615Packetizer.MAX_SOF_LENGTH + 1)
    p = Arinc615Packetizer(too_big)
    try:
        p.to_words()
        assert False, "Expected ValueError for oversized payload"
    except ValueError:
        pass
