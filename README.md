# PyARINC429

PyARINC429 is a maintained fork of the original ARINC 429 library by Jason Hodge.  
It provides Python types and utilities for encoding and decoding ARINC 429 words, along with extended support for ARINC 615 framing and a complete Williamsburg block‑transfer engine.

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
    loader.py
    williamsburg.py
```

---

## Word

Represents a 32‑bit ARINC 429 word.

### Properties

- label  
- sdi  
- data  
- ssm  
- parity  
- parity_type  
- parity_ok  
- raw

### Methods

- get_bit_field(lsb, msb)  
- set_bit_field(lsb, msb, value)  
- from_int(value, parity_type)  
- to_int()  
- copy()  
- with_fields(label=…, sdi=…, data=…, ssm=…)  
- as_dict()  
- to_json(indent=None)  
- validate(raise_on_error=False)

Bit‑field operations enforce range checks and recompute parity.

---

## WordBuilder

Fluent builder for constructing words.

```python
from arinc429.builder import WordBuilder

w = (
    WordBuilder()
    .label(0o123)
    .sdi(1)
    .data(0x55AA)
    .ssm(2)
    .parity_type(Word.EVEN_PARITY)
    .strict_parity(True)
    .build()
)
```

Unknown attributes raise `ValueError`.  
Overflow raises `FieldOverflowError`.  
`strict_parity(True)` enforces parity correctness.

---

## Data types

### BCD

```python
BCD(value, resolution)
```

Attributes: decoded, encoded, resolution, sign  
Methods: decode, copy, with_resolution, as_dict, to_json

### BNR

```python
BNR(value, resolution)
```

Attributes: decoded, encoded, resolution  
Methods: decode, copy, with_resolution, as_dict, to_json

### Discrete

```python
Discrete(value)
```

Attributes: decoded, encoded  
Methods: decode, copy, as_dict, to_json

---

## Label metadata

`labelinfo.py` defines metadata for ARINC labels:

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

- EQUIP_ADC  
- EQUIP_IRS  
- EQUIP_ALL

Helpers:

```python
decode_word(word, definitions)
merge_definitions(*equip_sets)
```

---

## High‑level API

```python
from arinc429.api import combine_definitions
from arinc429.definitions import EQUIP_ADC, EQUIP_IRS

custom = combine_definitions(EQUIP_ADC, EQUIP_IRS)
```

---

## ARINC615 packetizer

A simple framing model for ARINC 615 byte streams.

- SOF carries payload length.  
- DATA words carry 2 bytes each.  
- Final block is padded.  
- EOF carries zero.  
- `decode()` reconstructs the payload using the SOF length.

Example:

```python
from arinc429.loader import Arinc615Packetizer

p = Arinc615Packetizer(b"HELLO")
words = p.to_words()
decoded = Arinc615Packetizer.decode(words)
assert decoded == b"HELLO"
```

---

## Williamsburg protocol engine

`williamsburg.py` implements a complete ARINC 429 Williamsburg block‑transfer state machine.

Features:

- SAL / RTS / CTS / SOF / DATA / EOF / ACK / NAK control words  
- 3‑bit control‑code packing into the 19‑bit data field  
- CRC‑16‑CCITT integrity check  
- Automatic 2‑byte ARINC padding  
- Underflow detection  
- CRC mismatch detection  
- Round‑trip reconstruction of arbitrary payloads

### Transmitter

```python
tx = WilliamsburgSession(is_transmitter=True)
sal = tx.initiate_transfer(b"HELLO")
transfer = tx.process_incoming_word(rts_word)
```

### Receiver

```python
rx = WilliamsburgSession(is_transmitter=False)

ack = None
for w in transfer:
    r = rx.process_incoming_word(w)
    if r is not None:
        ack = r

assert rx.get_received_data() == b"HELLO"
```

The receiver trims padding using the SAL length and validates CRC before acknowledging.

---

## Validation

```python
w = Word()
errors = w.validate(raise_on_error=False)
if errors:
    print(errors)
```
