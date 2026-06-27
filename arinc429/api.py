from arinc429.definitions import EQUIP_ADC, EQUIP_IRS, decode_word
from arinc429.word import Word

DEFAULT_DEFINITIONS = {**EQUIP_ADC, **EQUIP_IRS}


def decode(raw: int, definitions=DEFAULT_DEFINITIONS):
    w = Word.from_int(raw)
    return decode_word(w, definitions)


def validate(raw: int, definitions=DEFAULT_DEFINITIONS):
    w = Word.from_int(raw)
    return w.validate_by_label(definitions)


def decode_and_validate(raw: int, definitions=DEFAULT_DEFINITIONS):
    w = Word.from_int(raw)
    decoded = decode_word(w, definitions)
    errors = w.validate_by_label(definitions)
    return decoded, errors
