# PyARINC429

PyARINC429 is a maintained fork of the original work by Jason Hodge.  
It provides Python types for encoding and decoding ARINC 429 words:

- BCD  
- BNR  
- Discrete  
- Mixed fields  
- Bit‑field extraction and validation  
- Parity computation  
- Label bit‑reversal  
- Optional label metadata  
- A fluent WordBuilder  

The library targets Python 3.12 and uses type annotations.

## Installation

```bash
git clone https://github.com/yourusername/PyARINC429
cd PyARINC429
pip install .
```

Tests:

```bash
pip install .[test]
pytest
```

## Package structure

```
arinc429/
    word.py
    bitfields.py
    errors.py
    builder.py
    definitions.py
    datatypes/
        base.py
        bcd.py
        bnr.py
        discrete.py
```

## Word

Represents a 32‑bit ARINC 429 word.

### Properties

- **label** — octal label (0o000–0o377), bit‑reversed on write  
- **sdi** — 2‑bit SDI  
- **data** — bits 11–29 (19 bits)  
- **ssm** — 2‑bit SSM  
- **parity** — stored parity bit  
- **parity_type** — `ODD_PARITY` or `EVEN_PARITY`  
- **parity_ok** — computed parity check  
- **raw** — underlying integer  

### Methods

- **get_bit_field(lsb, msb)**  
- **set_bit_field(lsb, msb, value)**  
- **from_int(value, parity_type)**  
- **to_int()**  
- **copy()**  
- **with_fields(label=…, sdi=…, data=…, ssm=…)**  
- **as_dict()**  
- **validate(raise_on_error=False)**  

### Bit‑field rules

- All bitfields use **signed two’s‑complement** range checks.  
- Overflow raises `FieldOverflowError`.  
- Parity is recomputed after every write.

### Data‑field integer semantics

`int(BNR|BCD|Discrete)` returns the **encoded on‑wire integer**.  
`float(...)`, `str(...)`, and `.decoded` return the semantic value.

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
    .build()
)
```

### Builder rules

- Unknown private attributes (e.g., `b._unexpected = 1`) raise `ValueError`.  
- `FieldOverflowError` propagates.  
- Other exceptions are wrapped in `ValueError`.  

## BCD

```python
BCD(value, resolution)
```

Attributes:

- **decoded**  
- **encoded**  
- **resolution**  
- **sign**

Methods:

- **decode(bcd_value, ssm, resolution)**  
- **copy()**  
- **with_resolution(r)**  
- **as_dict()**

## BNR

```python
BNR(value, resolution)
```

Attributes:

- **decoded**  
- **encoded**  
- **resolution**

Methods:

- **decode(value, bit_length, resolution)**  
- **copy()**  
- **with_resolution(r)**  
- **as_dict()**

## Discrete

```python
Discrete(value)
```

Attributes:

- **decoded**  
- **encoded**

Methods:

- **decode(value)**  
- **copy()**  
- **as_dict()**

## definitions

Metadata for optional label‑based decoding.

```python
LabelDefinition(name, type, resolution, unit=None)
EQUIP_ADC
EQUIP_IRS
```

Helper:

```python
decode_word(word, definitions) -> (data_field, definition) | None
```

## ARINC615 Packetizer

- Splits a byte stream into ARINC 429 words.  
- SOF carries payload length.  
- DATA words carry 2 bytes each.  
- EOF always has data field = 0.  
- Padding is removed on decode.

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

## Decoding with metadata

```python
from arinc429 import Word
from arinc429.definitions import EQUIP_ADC, decode_word

w = Word()
w.label = 0o203
decoded = decode_word(w, EQUIP_ADC)
```

## Validation

```python
w = Word()
errors = w.validate(raise_on_error=False)
if errors:
    print(errors)
```
