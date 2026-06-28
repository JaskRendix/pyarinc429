# PyARINC429

PyARINC429 is a maintained fork of the original ARINC 429 library by Jason Hodge.  
It provides Python types and utilities for encoding and decoding ARINC 429 words.

**Original repository:** [https://github.com/aeroneous/PyARINC429](https://github.com/aeroneous/PyARINC429)

---

## Installation

```bash
git clone https://github.com/JaskRendix/pyarinc429
cd pyarinc429
pip install .
```

Tests:

```bash
pip install .[test]
pytest
```

---

## Package layout

```
arinc429/
    word.py
    bitfields.py
    errors.py
    builder.py
    definitions.py
    labelinfo.py
    labels.py
    datatypes/
        base.py
        bcd.py
        bnr.py
        discrete.py
```

---

## Word

Represents a 32‑bit ARINC 429 word.

### Properties

- **label** — octal label (0o000–0o377), bit‑reversed on write  
- **sdi** — 2‑bit SDI  
- **data** — bits 11–29  
- **ssm** — 2‑bit SSM  
- **parity** — stored parity bit  
- **parity_type** — `ODD_PARITY` or `EVEN_PARITY`  
- **parity_ok** — computed parity check  
- **raw** — underlying integer

### Methods

- **get_bit_field**(lsb, msb)  
- **set_bit_field**(lsb, msb, value)  
- **from_int**(value, parity_type)  
- **to_int**()  
- **copy**()  
- **with_fields**(label=…, sdi=…, data=…, ssm=…)  
- **as_dict**()  
- **validate**(raise_on_error=False)

### Bit‑field rules

- All bitfields use signed two’s‑complement range checks.  
- Overflow raises `FieldOverflowError`.  
- Parity is recomputed after each write.

### Data‑field integer semantics

- `int(BNR|BCD|Discrete)` returns the encoded integer.  
- `float(...)`, `str(...)`, and `.decoded` return the decoded value.

---

## WordBuilder

Fluent builder for constructing words.

```python
from arinc429.builder import WordBuilder
from arinc429.word import Word

w = (
    WordBuilder()
    .label(0o123)
    .sdi(1)
    .data(0x55AA)
    .ssm(2)
    .parity_type(Word.EVEN_PARITY)
    .build()
)
```

Builder rules:

- Unknown attributes raise `ValueError`.  
- `FieldOverflowError` propagates.  
- Other exceptions are wrapped in `ValueError`.

---

## Data types

### BCD

```python
BCD(value, resolution)
```

Attributes: `decoded`, `encoded`, `resolution`, `sign`  
Methods: `decode`, `copy`, `with_resolution`, `as_dict`

### BNR

```python
BNR(value, resolution)
```

Attributes: `decoded`, `encoded`, `resolution`  
Methods: `decode`, `copy`, `with_resolution`, `as_dict`

### Discrete

```python
Discrete(value)
```

Attributes: `decoded`, `encoded`  
Methods: `decode`, `copy`, `as_dict`

---

## Label metadata

`labelinfo.py` defines:

```python
LabelInfo(label, name, system, category, direction=None, description=None)
LABEL_INFO
get_label_info()
require_label_info()
```

Metadata attaches to `LabelDefinition` through `attach_info()`.

---

## Definitions

Defines decoding schemas for known labels.

```python
FieldDefinition(name, lsb, msb, type, resolution=None, unit=None)
LabelDefinition(name, fields, info=None)
```

Equipment sets:

- `EQUIP_ADC`  
- `EQUIP_IRS`

Helper:

```python
decode_word(word, definitions)
    -> (decoded_fields, LabelDefinition, LabelInfo | None)
    -> None if label not in definitions
```

---

## Decoding with metadata

```python
from arinc429 import Word
from arinc429.definitions import EQUIP_ADC, decode_word

w = Word()
w.label = 0o203

decoded_fields, definition, info = decode_word(w, EQUIP_ADC)

print(decoded_fields)
print(definition.name)
print(info.system)
```

---

## ARINC615 packetizer

A simplified model of ARINC 615 framing: no sequence counters, no
checksums, no load-list metadata. Real ARINC 615 includes these; this
class exists for basic byte-stream chunking into ARINC 429 words.

- `to_words()` splits a byte stream into ARINC 429 words: a leading SOF
  word, followed by DATA words, followed by a single EOF word.
- The SOF word (label `CONTROL_LABEL_SOF`) carries the exact payload
  length in its data field, so the original length can be recovered
  precisely on decode rather than guessed from padding. Payloads larger
  than `MAX_SOF_LENGTH` bytes raise `ValueError`, since the length
  wouldn't fit in the 19-bit field.
- DATA words (label `CONTROL_LABEL_DATA`) carry 2 bytes each, big-endian.
  The final block is zero-padded on the right if the input length isn't
  a multiple of 2.
- The EOF word (label `CONTROL_LABEL_EOF`) has a zero data field.
- `decode(words)` reconstructs the original payload from a list of
  words: it reads the length from the first SOF word seen (later SOF
  words, if any, are ignored), concatenates the data field of every
  DATA-labeled word in order, and trims the result to exactly that
  length. Non-DATA, non-SOF words (EOF, or any unexpected/corrupted
  word) are ignored.
- If no SOF word is present in the list (e.g. a hand-built or legacy
  word list), `decode()` falls back to stripping trailing null bytes.
  This fallback has the original limitation: a payload that itself ends
  in null bytes will have those bytes stripped too. This only applies
  to the no-SOF fallback path; word lists produced by `to_words()`
  always carry a SOF and round-trip exactly, including trailing nulls.

```python
from arinc429.loader import Arinc615Packetizer

p = Arinc615Packetizer(b"HELLO")
words = p.to_words()

decoded = Arinc615Packetizer.decode(words)
assert decoded == b"HELLO"
```

---

## WilliamsburgTransmitter / WilliamsburgReceiver

Simple SOF/DATA/EOF framing.

Rules:

- Unexpected label aborts the frame.  
- EOF after abort returns `None`.  
- Padding trimmed using SOF length.

Example:

```python
from arinc429 import WilliamsburgTransmitter, WilliamsburgReceiver

tx = WilliamsburgTransmitter()
words = tx.encode(b"HELLO")

rx = WilliamsburgReceiver()
out = None
for w in words:
    r = rx.process_word(w)
    if r is not None:
        out = r

assert out == b"HELLO"
```

---

## Validation

```python
w = Word()
errors = w.validate(raise_on_error=False)
if errors:
    print(errors)
```
