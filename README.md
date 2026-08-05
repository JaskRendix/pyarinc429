# pyarinc429

pyarinc429 is a maintained fork of the original ARINC 429 library by Jason Hodge.  
It provides Python types and utilities for encoding and decoding ARINC 429 words, ARINC 615 framing, Williamsburg block‑transfer, ICD metadata loading, and a full ARINC 429 **simulation engine**.

**Original repository:** [https://github.com/aeroneous/PyARINC429](https://github.com/aeroneous/PyARINC429)

---

## Installation

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
    icd.py
    sim.py
    cli.py
examples/
    flight_sim.py
    multi_fault_sim.py
    high_rate_stress_test.py
```

---

## Word

Represents a 32‑bit ARINC 429 word with full bit‑field manipulation and parity handling.

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

## Data types

### BCD / BNR / Discrete

Typed decoding helpers for ARINC 429 numeric formats.

---

## Label metadata

Metadata for ARINC labels:

```python
LabelInfo(label, name, system, category, direction=None, description=None)
LABEL_INFO
get_label_info()
require_label_info()
```

---

## Definitions

Decoding schemas for known labels:

```python
FieldDefinition(name, lsb, msb, type, resolution=None, unit=None)
LabelDefinition(name, fields, info=None)
```

Equipment sets:

- EQUIP_ADC  
- EQUIP_IRS  
- EQUIP_ALL

---

## High‑level API

```python
from arinc429.api import combine_definitions
custom = combine_definitions(EQUIP_ADC, EQUIP_IRS)
```

---

## ARINC 615 packetizer

Framing model for ARINC 615 byte streams.

```python
from arinc429.loader import Arinc615Packetizer

p = Arinc615Packetizer(b"HELLO")
words = p.to_words()
decoded = Arinc615Packetizer.decode(words)
```

---

## Williamsburg protocol engine

Implements the ARINC 429 Williamsburg block‑transfer state machine with CRC‑16‑CCITT, padding, and control‑word sequencing.

---

## ICD loader

Load external ICD metadata from JSON:

```python
from arinc429.icd import load_icd_json
load_icd_json("icd.json")
```

---

# **Simulation Engine (`arinc429.sim`)**

The simulation module provides a full ARINC 429 virtual databus:

### Components

- **ArincBus** — thread‑safe shared bus with timestamped logging  
- **VirtualNode** — transmitter/receiver LRU with periodic scheduling  
- **BusMonitor** — passive sniffer with parity tracking and label filtering  
- **FaultyVirtualNode** — injects faults (drops, bit flips, parity corruption)  
- **stop_all()** — clean shutdown helper  

### Example usage

```python
from arinc429.sim import ArincBus, VirtualNode, BusMonitor

bus = ArincBus()
monitor = BusMonitor("MON", bus)

adc = VirtualNode("ADC", bus)
adc.register_periodic_transmission(lambda: WordBuilder().label(0o203).data(0x1234).build(), rate_hz=20)
adc.start()
```

---

# **CLI**

The project provides a command‑line interface under the executable name `pyarinc`.

---

## Decode a raw ARINC 429 word

```bash
pyarinc decode 0x9c000c26
pyarinc decode 0x9c000c26 --json
pyarinc decode 0x9c000c26 --profile adc
```

---

## ARINC 615 packetization

```bash
pyarinc arinc615-encode "HELLO"
pyarinc arinc615-encode --file payload.bin
pyarinc arinc615-encode "HELLO" --output words.json
```

---

## Williamsburg block‑transfer simulation

```bash
pyarinc williamsburg-simulate "HELLO"
pyarinc williamsburg-simulate "HELLO" --trace
```

---

## Load ICD metadata

```bash
pyarinc load-icd icd.json
```

---

# **Bus Simulation (CLI)**

The simulation engine is accessible directly from the CLI:

```bash
pyarinc simulate --duration 2.0
pyarinc simulate --duration 2.0 --faulty
```

This spins up:

- ADC node  
- IRS node  
- optional faulty node  
- BusMonitor  
- periodic transmissions  
- parity/error tracking  
- summary report  

---

# **Examples**

Three complete examples are included under `examples/`.

---

## **1. Flight Simulation (`flight_sim.py`)**

Simulates:

- ADC altitude  
- IRS heading  
- FMC receiving both  
- BusMonitor auditing  
- Faulty ADC injected mid‑flight  

Demonstrates realistic avionics data flow.

---

## **2. Multi‑Fault Scenario (`multi_fault_sim.py`)**

Simulates compound failures:

- parity corruption  
- bit flips  
- wrong labels  
- packet drops  
- silent node  
- anomaly detection in Flight Director  

Demonstrates robustness under chaotic conditions.

---

## **3. High‑Rate Stress Test (`high_rate_stress_test.py`)**

Simulates extreme bus load:

- nodes transmitting at 100–500 Hz  
- faulty node at 150 Hz  
- saturation behavior  
- throughput measurement  
- parity error accumulation  

Demonstrates scheduler and bus performance under stress.
