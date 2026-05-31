# PyARINC429

PyARINC429 is a maintained fork of the original work by Jason Hodge:  
<https://github.com/aeroneous/PyARINC429>

The library provides Python types for encoding and decoding ARINC 429 words:

- BCD  
- BNR  
- Discrete fields  
- Mixed BCD/discrete and BNR/discrete fields  
- Bit‑field extraction and validation  
- Parity computation  
- Label bit‑reversal  
- Optional label metadata  
- A builder for constructing words  

The library targets Python 3.12 and uses type annotations.

## Installation

```bash
git clone https://github.com/yourusername/PyARINC429
cd PyARINC429
pip install .
```

Install test dependencies:

```bash
pip install .[test]
```

Run tests:

```bash
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

## API Reference

### Word

Represents a 32‑bit ARINC 429 word.  
Parity is recomputed when any bit‑field is written.

Properties:

- label — octal label (0o000–0o377), bit‑reversed on write  
- sdi — Source/Destination Identifier (2 bits)  
- data — bits 11–29 (19 bits)  
- ssm — Sign/Status Matrix (2 bits)  
- parity — computed from bits 1–31  
- parity_type — ODD_PARITY or EVEN_PARITY  
- parity_ok — parity check result  
- raw — underlying integer value  

Methods:

- get_bit_field(lsb, msb)  
- set_bit_field(lsb, msb, value)  
- from_int(value, parity_type)  
- to_int()  
- copy()  
- with_fields(label=..., sdi=..., data=..., ssm=...)  
- as_dict()  

Parity notes:

- `parity_type` controls whether the word uses odd or even parity. The library
    computes and updates the parity bit automatically whenever a bit field is
    written (via `set_bit_field`). Use `parity_ok` to validate the stored parity
    against the computed value. `Word.validate()` performs a parity check and will
    raise if the parity bit does not match the configured `parity_type`.

Label metadata:

- `definitions.py` exposes `LabelDefinition` and sample equipment dictionaries
    (`EQUIP_ADC`, `EQUIP_IRS`). These provide optional metadata (name, type,
    resolution, unit) that can be used by higher-level decoding helpers. The
    package does not automatically apply `LabelDefinition` when decoding words —
    use the metadata as guidance for which `DataFieldType` (`BNR`, `BCD`,
    `Discrete`) to use when interpreting the `data` and `ssm` fields.

### WordBuilder

Fluent builder for constructing words:

```python
from arinc429.builder import WordBuilder

w = (
    WordBuilder()
    .label(0o123)
    .sdi(1)
    .data(0x55AA)
    .ssm(2)
    .build()
)
```

### BCD

Constructor:

```python
BCD(value, resolution)
```

Attributes:

- decoded  
- encoded  
- resolution  
- sign  

Methods:

- decode(bcd_value, bcd_sign, resolution)  
- copy()  
- with_resolution(new_resolution)  
- as_dict()  

### BNR

Constructor:

```python
BNR(value, resolution)
```

Attributes:

- decoded  
- encoded  
- resolution  

Methods:

- decode(bnr_value, bit_length, resolution)  
- copy()  
- with_resolution(new_resolution)  
- as_dict()  

### Discrete

Constructor:

```python
Discrete(value)
```

Attributes:

- decoded  
- encoded  

Methods:

- decode(value)  
- copy()  
- as_dict()  

### definitions

Optional label metadata:

```python
LabelDefinition(name, type, resolution, unit=None)
EQUIP_ADC
EQUIP_IRS
```

### loader.Arinc615Packetizer

Splits a byte stream into ARINC 429 words using control labels.

### williamsburg.WilliamsburgTransmitter

Encodes a byte stream into Williamsburg block‑transfer words.

### williamsburg.WilliamsburgReceiver

Reassembles Williamsburg frames into a byte stream.

## Examples

### BCD

```python
word = arinc429.Word()
word.label = 0o1
encoded = arinc429.BCD(121.5, resolution=0.1)
word.set_bit_field(11, 29, encoded)
decoded = arinc429.BCD.decode(word.data, word.ssm, 0.1)
```

### BNR

```python
word = arinc429.Word()
word.label = 0o2
encoded = arinc429.BNR(90, 0.043945313)
word.set_bit_field(13, 29, encoded)
word.set_bit_field(11, 12, arinc429.Discrete(1))
decoded = arinc429.BNR.decode(
    word.get_bit_field(bnr_field.lsb, bnr_field.msb),
    17,
    0.043945313
)
```

### Discrete

```python
word = arinc429.Word()
word.label = 0o3
encoded = arinc429.Discrete(6)
word.set_bit_field(11, 13, encoded)
decoded = arinc429.Discrete.decode(word.data)
```

### Williamsburg (SOF/DATA/EOF block transfer)

The package exports both `WilliamsburgTransmitter` and `WilliamsburgReceiver` at
the package root for convenience. These helpers implement a simple SOF/DATA/EOF
block transfer framing for packing small byte streams into ARINC 429 words.

Example (transmit + receive):

```python
from arinc429 import WilliamsburgTransmitter, WilliamsburgReceiver

tx = WilliamsburgTransmitter()
words = tx.encode(b"HELLO")

rx = WilliamsburgReceiver()
result = None
for w in words:
    out = rx.process_word(w)
    if out is not None:
        result = out

assert result == b"HELLO"
```
