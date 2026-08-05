# **pyarinc429**

`pyarinc429` is a separate ARINC 429 library derived from the original implementation by Jason Hodge.  
It expands the original project with additional ARINC 429 utilities, ICD metadata handling, ICD‑driven code generation, ARINC 615 framing, Williamsburg block‑transfer, and a full ARINC 429 simulation engine.

**Original repository:**  
[https://github.com/aeroneous/PyARINC429](https://github.com/aeroneous/PyARINC429)

---

## **Installation**

```bash
git clone https://github.com/JaskRendix/pyarinc429
cd pyarinc429
pip install .
```

Run tests:

```bash
pip install .[test]
pytest
```

---

## **Package layout**

```text
arinc429/
    word.py
    bitfields.py
    decode.py
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
    icd.py
    sim.py
    drivers.py
    cli.py
examples/
    README.md
    flight_sim.py
    multi_fault_sim.py
    high_rate_stress_test.py
    datatypes_integration.py
    record_and_replay.py
```

---

# **Word**

`Word` represents a 32‑bit ARINC 429 word with full bit‑field access and parity handling.

Fields:

- label  
- sdi  
- data  
- ssm  
- parity  
- parity_type  
- parity_ok  
- raw  

Methods:

- `get_bit_field(lsb, msb)`  
- `set_bit_field(lsb, msb, value)`  
- `from_int(value, parity_type)`  
- `to_int()`  
- `copy()`  
- `with_fields(...)`  
- `as_dict()`  
- `to_json()`  
- `validate()`  

---

# **WordBuilder**

Fluent builder for constructing valid ARINC 429 words.

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

---

# **Datatypes**

Typed helpers for decoding ARINC 429 numeric formats:

- BCD  
- BNR  
- Discrete  

Each datatype supports:

- encoded / decoded values  
- resolution  
- numeric conversion  
- JSON serialization  

---

# **Label metadata**

Metadata for ARINC 429 labels:

```python
LabelInfo(label, name, system, category, direction=None, description=None)
LABEL_INFO
get_label_info()
require_label_info()
```

---

# **Definitions**

Structures for ICD‑driven decoding:

```python
FieldDefinition(name, lsb, msb, type, resolution=None, unit=None)
LabelDefinition(name, fields, info=None)
```

Equipment sets:

- `EQUIP_ADC`  
- `EQUIP_IRS`  
- `EQUIP_ALL`  

Combine sets:

```python
from arinc429.api import combine_definitions
custom = combine_definitions(EQUIP_ADC, EQUIP_IRS)
```

---

# **ARINC 615 packetizer**

```python
from arinc429.loader import Arinc615Packetizer

p = Arinc615Packetizer(b"HELLO")
words = p.to_words()
decoded = Arinc615Packetizer.decode(words)
```

---

# **Williamsburg protocol engine**

Implements the ARINC 429 Williamsburg block‑transfer state machine with CRC‑16‑CCITT, padding, and control‑word sequencing.

---

# **ICD loader**

```python
from arinc429.icd import load_icd_json
labels = load_icd_json("icd.json")
```

---

# **ICD code generator**

Generate Python dataclasses and decoders from an ICD JSON file:

```bash
pyarinc generate icd.json
pyarinc generate icd.json --output custom_icd.py
```

The generated module contains:

- one dataclass per label  
- a `from_word()` decoder for each dataclass  
- an `ICD_REGISTRY` mapping label → dataclass  
- a `decode_icd_word()` helper  

BNR fields are sign‑extended from their defined width.  
BCD fields derive their sign from SSM bits.

---

# **Simulation engine (`arinc429.sim`)**

Provides a virtual ARINC 429 databus.

Components:

- `ArincBus`  
- `VirtualNode`  
- `BusMonitor`  
- `FaultConfig`  
- `FaultyVirtualNode`  
- `BusRecorder`  
- `ReplayNode`  
- `stop_all()`  

Example:

```python
from arinc429.sim import ArincBus, VirtualNode, BusMonitor, BusRecorder, ReplayNode, stop_all
from arinc429.builder import WordBuilder
import time
from pathlib import Path

bus = ArincBus()
monitor = BusMonitor("MON", bus)

adc = VirtualNode("ADC", bus)
adc.register_periodic_transmission(
    lambda: WordBuilder().label(0o203).data(0x1234).build(),
    rate_hz=20.0,
)
adc.start()

time.sleep(1.0)
stop_all([adc])

log_file = Path("record.jsonl")
BusRecorder.export_to_jsonl(monitor.captured_words, log_file)

replay_bus = ArincBus()
replay_monitor = BusMonitor("REPLAY_MON", replay_bus)
ReplayNode(log_file, replay_bus, speed_multiplier=2.0).play()
```

---

# **Hardware drivers (`arinc429.drivers`)**

Transport layer:

- `ArincTransport`  
- `SerialTransport`  
- `SocketTransport`  

Driver layer:

- `BaseArincDriver`  
- `AsyncBusTransportDriver`  

Drivers bridge physical ARINC 429 hardware (serial adapters, UDP/TCP gateways) with the virtual bus.

---

# **CLI (`pyarinc`)**

Command‑line interface for decoding, packetizing, Williamsburg simulation, ICD loading, ICD code generation, and bus simulation.

### Decode a raw word

```bash
pyarinc decode 0x9c000c26
pyarinc decode 0x9c000c26 --json
pyarinc decode 0x9c000c26 --profile adc --parity even
```

### ARINC 615 packetization

```bash
pyarinc arinc615-encode "HELLO"
pyarinc arinc615-encode --file payload.bin
```

### Williamsburg simulation

```bash
pyarinc williamsburg-simulate "HELLO"
```

### Load ICD metadata

```bash
pyarinc load-icd icd.json
```

### Generate ICD module

```bash
pyarinc generate icd.json
pyarinc generate icd.json --output custom_icd.py
```

### Bus simulation

```bash
pyarinc simulate --duration 2.0
pyarinc simulate --duration 2.0 --faulty
```

### Replay recorded traffic

```bash
pyarinc replay flight_recording.jsonl --speed 1.0
```

---

# **Examples**

See:

```
examples/README.md
```

for descriptions of:

- `flight_sim.py`  
- `multi_fault_sim.py`  
- `high_rate_stress_test.py`  
- `datatypes_integration.py`  
- `record_and_replay.py`  
