# PyARINC429

This project is a maintained and modernized fork of the original work by Jason Hodge:  
[https://github.com/aeroneous/PyARINC429](https://github.com/aeroneous/PyARINC429)

PyARINC429 provides Python types for encoding and decoding ARINC 429 words.  
It implements:

- Binary Coded Decimal (BCD)  
- Binary Number Representation (BNR)  
- Discrete fields  
- Mixed BCD/discrete and BNR/discrete fields  
- Bit‑field extraction and validation  
- Automatic parity handling  
- Label bit‑reversal per ARINC 429  

The library targets Python 3.12 and uses modern typing.

---

## Installation

Install from source:

```bash
git clone https://github.com/yourusername/PyARINC429
cd PyARINC429
pip install .
```

Install with test dependencies:

```bash
pip install .[test]
```

Run the test suite:

```bash
pytest
```

---

## API Reference

### `Word`

Represents a 32‑bit ARINC 429 word.

**Properties**

- `label` — octal label (0o000–0o377), bit‑reversed on write  
- `sdi` — Source/Destination Identifier  
- `data` — bits 11–29  
- `ssm` — Sign/Status Matrix  
- `parity` — computed automatically  
- `parity_type` — `Word.ODD_PARITY` or `Word.EVEN_PARITY`

**Methods**

- `get_bit_field(lsb, msb)`  
- `set_bit_field(lsb, msb, value)`  

---

### `DataField`

Defines a bit‑field slice:

```python
DataField(lsb: int, msb: int, data: int | DataFieldType)
```

Useful for passing directly into `Word.set_bit_field(*field)`.

---

### `BCD`

Binary Coded Decimal encoder/decoder.

**Constructor**

```python
BCD(value, resolution)
```

**Attributes**

- `resolution`  
- `sign`  
- `_decoded_value`  

**Classmethod**

```python
BCD.decode(bcd_value, bcd_sign, resolution)
```

---

### `BNR`

Binary Number Representation encoder/decoder.

**Constructor**

```python
BNR(value, resolution)
```

**Classmethod**

```python
BNR.decode(bnr_value, bit_length, resolution)
```

Handles two’s complement sign extension.

---

### `Discrete`

Represents a discrete bit‑field.

**Constructor**

```python
Discrete(value)
```

**Classmethod**

```python
Discrete.decode(value)
```

---

### `definitions`

Provides optional label metadata.

```python
LabelDefinition(name, type, resolution, unit=None)
EQUIP_ADC
EQUIP_IRS
```

---

### `loader.Arinc615Packetizer`

Simple ARINC 615‑style packetizer.  
Splits a byte stream into ARINC 429 words using control labels.

---

### `williamsburg.WilliamsburgTransmitter`

Encodes a byte stream into Williamsburg block‑transfer words.

### `williamsburg.WilliamsburgReceiver`

Reassembles Williamsburg frames into a byte stream.

---

## Examples

### BCD

```python
>>> word = arinc429.Word()
>>> word.label = 0o1
>>> encoded = arinc429.BCD(121.5, resolution=0.1)
>>> field = arinc429.DataField(11, 29, encoded)
>>> word.set_bit_field(*field)
>>> print(word)
Label=0o1, SDI=0, Data=0x1215, SSM=0, Parity=0
>>> decoded = arinc429.BCD.decode(word.data, word.ssm, 0.1)
>>> print(decoded)
121.5
```

### BNR

```python
>>> word = arinc429.Word()
>>> word.label = 0o2
>>> encoded = arinc429.BNR(90, 0.043945313)
>>> bnr_field = arinc429.DataField(13, 29, encoded)
>>> disc_field = arinc429.DataField(11, 12, arinc429.Discrete(1))
>>> word.set_bit_field(*bnr_field)
>>> print(word)
Label=0o2, SDI=0, Data=0x1ffc, SSM=0, Parity=1
>>> word.set_bit_field(*disc_field)
>>> print(word)
Label=0o2, SDI=0, Data=0x1ffd, SSM=0, Parity=0
>>> decoded = arinc429.BNR.decode(
...     word.get_bit_field(bnr_field.lsb, bnr_field.msb),
...     17,
...     0.043945313
... )
>>> print(decoded)
BNR(value=89.956055711, resolution=0.043945313)
```

### Discrete

```python
>>> word = arinc429.Word()
>>> word.label = 0o3
>>> encoded = arinc429.Discrete(6)
>>> field = arinc429.DataField(11, 12, encoded)
>>> word.set_bit_field(*field)
arinc429.arinc429.FieldOverflowError: 0x6 overflows 2 bit(s)
>>> field = arinc429.DataField(11, 13, encoded)
>>> word.set_bit_field(*field)
>>> print(word)
Label=0o3, SDI=0, Data=0x6, SSM=0, Parity=0
>>> decoded = arinc429.Discrete.decode(word.data)
>>> print(decoded)
6
```
