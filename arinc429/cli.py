from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

from arinc429.api import combine_definitions, decode_and_validate
from arinc429.definitions import EQUIP_ADC, EQUIP_IRS, EQUIP_ALL, LabelDefinition
from arinc429.loader import Arinc615Packetizer
from arinc429.icd import load_icd_json
from arinc429.williamsburg import WilliamsburgSession
from arinc429.word import Word

EQUIP_MAP: dict[str, dict[int, LabelDefinition]] = {
    "adc": EQUIP_ADC,
    "irs": EQUIP_IRS,
    "all": EQUIP_ALL,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI tool for PyARINC429.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Decode command
    decode_parser = subparsers.add_parser("decode", help="Decode a raw ARINC 429 word.")
    decode_parser.add_argument("raw_word", help="Raw ARINC 429 word in hex (e.g., 0x9c000c26) or decimal.")
    decode_parser.add_argument("-p", "--profile", default="all", choices=["adc", "irs", "all"], help="Equipment profile.")
    decode_parser.add_argument("--parity", default="odd", choices=["odd", "even"], help="Parity type.")
    decode_parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format.")

    # ARINC 615 encode command
    encode_parser = subparsers.add_parser("arinc615-encode", help="Encode payload to ARINC 615 words.")
    encode_parser.add_argument("payload", nargs="?", help="String payload to packetize.")
    encode_parser.add_argument("-f", "--file", type=Path, help="Read payload from file.")
    encode_parser.add_argument("-o", "--output", type=Path, help="Optional output file for JSON words.")

    # Williamsburg simulation command
    sim_parser = subparsers.add_parser("williamsburg-simulate", help="Simulate a Williamsburg block transfer.")
    sim_parser.add_argument("message", help="Payload message to transfer.")
    sim_parser.add_argument("--trace", action="store_true", help="Print control-word sequence.")

    # ICD Load command
    icd_parser = subparsers.add_parser("load-icd", help="Load custom label definitions from an ICD JSON file.")
    icd_parser.add_argument("icd_file", type=Path, help="Path to ICD JSON metadata file.")

    # ICD Code Generation command
    gen_parser = subparsers.add_parser("generate", help="Generate typed Python dataclasses from an ICD JSON file.")
    gen_parser.add_argument("icd_file", type=Path, help="Path to ICD JSON metadata file.")
    gen_parser.add_argument("-o", "--output", type=Path, help="Output Python file path (defaults to stdout).")

    # Bus simulation command
    sim_bus_parser = subparsers.add_parser("simulate", help="Run a live multi-node ARINC 429 bus simulation.")
    sim_bus_parser.add_argument("--duration", type=float, default=2.0, help="Simulation duration in seconds.")
    sim_bus_parser.add_argument("--faulty", action="store_true", help="Introduce a faulty node to test parity and error monitoring.")

    # Replay simulation command
    replay_parser = subparsers.add_parser("replay", help="Replay a recorded JSONL ARINC 429 traffic file.")
    replay_parser.add_argument("record_file", type=Path, help="Path to recorded JSONL file.")
    replay_parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier.")

    args = parser.parse_args()

    if args.command == "decode":
        try:
            val = int(args.raw_word, 0)
        except ValueError:
            print(f"Error: Invalid integer/hex format for word: {args.raw_word}")
            raise SystemExit(1)

        p_type = Word.EVEN_PARITY if args.parity == "even" else Word.ODD_PARITY
        defs = EQUIP_MAP.get(args.profile, EQUIP_ALL)

        res, errors = decode_and_validate(val, definitions=defs, parity_type=p_type, report_unknown=True)
        word_obj = Word.from_int(val, p_type)

        decoded: dict[str, object] = {}
        definition = None
        if res is not None:
            decoded, definition, _ = res

        if args.json:
            output_data = {
                "raw": hex(val),
                "label": hex(word_obj.label),
                "sdi": word_obj.sdi,
                "ssm": word_obj.ssm,
                "data": hex(word_obj.data),
                "definition": definition.name if definition else None,
                "decoded_fields": {k: str(v) for k, v in decoded.items()} if decoded else {},
                "errors": errors,
            }
            print(json.dumps(output_data, indent=2))
            return

        print("=== ARINC 429 Word Analysis ===")
        print(f"Raw Value   : {hex(val)} ({val})")
        print(f"Label (oct) : {word_obj.label:03o}")
        print(f"Parity OK   : {word_obj.parity_ok}")
        print(f"SDI         : {word_obj.sdi}")
        print(f"SSM         : {word_obj.ssm}")
        print(f"DATA bits   : {hex(word_obj.data)}")
        print(f"Definition  : {definition.name if definition else 'Unknown Label'}")
        
        if decoded:
            print("\nDecoded Fields:")
            for k, v in decoded.items():
                print(f"  - {k}: {v}")
        if errors:
            print("\nValidation Errors/Warnings:")
            for err in errors:
                print(f"  * {err}")

    elif args.command == "arinc615-encode":
        payload: bytes
        if args.file:
            try:
                payload = args.file.read_bytes()
            except Exception as e:
                print(f"Error reading file {args.file}: {e}")
                raise SystemExit(1)
        elif args.payload:
            payload = args.payload.encode("utf-8")
        else:
            print("Error: Either a payload string or a file (--file) must be provided.")
            raise SystemExit(1)

        try:
            p = Arinc615Packetizer(payload)
            words = p.to_words()
        except Exception as e:
            print(f"Error encoding ARINC 615 package: {e}")
            raise SystemExit(1)

        hex_words = [hex(w.to_int()) for w in words]
        if args.output:
            args.output.write_text(json.dumps(hex_words, indent=2), encoding="utf-8")
            print(f"Successfully wrote {len(words)} words to {args.output}")
        else:
            print(f"Generated {len(words)} ARINC 615 words:")
            for hw in hex_words:
                print(hw)

    elif args.command == "williamsburg-simulate":
        payload_bytes = args.message.encode("utf-8")
        print(f"Initializing Williamsburg transmitter session with payload: '{args.message}'")
        tx = WilliamsburgSession(is_transmitter=True)
        rx = WilliamsburgSession(is_transmitter=False)

        try:
            sal_words = tx.initiate_transfer(payload_bytes)
            if args.trace:
                print("SAL:", [hex(w.to_int()) for w in sal_words])

            rts_response = rx.process_incoming_word(sal_words[0])
            if args.trace and rts_response:
                print("RTS:", [hex(w.to_int()) for w in rts_response])

            if not rts_response:
                raise RuntimeError("Receiver did not respond to SAL with RTS")

            block_words = tx.process_incoming_word(rts_response[0])
            if args.trace and block_words:
                print("BLOCK:")
                for w in block_words:
                    print(" ", hex(w.to_int()))

            if not block_words:
                raise RuntimeError("Transmitter failed to generate data block")
            
            ack_response = None
            for w in block_words:
                resp = rx.process_incoming_word(w)
                if resp is not None:
                    ack_response = resp

            if ack_response:
                if args.trace:
                    print("ACK:", [hex(w.to_int()) for w in ack_response])
                tx.process_incoming_word(ack_response[0])

            recovered = rx.get_received_data()
            if recovered is None:
                raise RuntimeError("Failed to extract received data payload")
            print(f"\nSuccessfully reconstructed payload: {recovered.decode('utf-8')}")
        except Exception as e:
            print(f"Simulation failed with error: {e}")
            raise SystemExit(1)

    elif args.command == "load-icd":
        try:
            loaded = load_icd_json(args.icd_file)
            print(f"Successfully loaded {len(loaded)} label definitions from {args.icd_file}")
        except Exception as e:
            print(f"Error loading ICD file: {e}")
            raise SystemExit(1)

    elif args.command == "generate":
        from arinc429.icd import generate_icd_code
        try:
            code = generate_icd_code(args.icd_file)
            if args.output:
                args.output.write_text(code, encoding="utf-8")
                print(f"Successfully generated typed ICD code → {args.output}")
            else:
                print(code)
        except Exception as e:
            print(f"Error generating code from ICD: {e}")
            raise SystemExit(1)

        if args.output:
            args.output.write_text(code, encoding="utf-8")
            print(f"Successfully generated typed ICD code → {args.output}")
        else:
            print(code)

    elif args.command == "simulate":
        from arinc429.sim import ArincBus, VirtualNode, BusMonitor, FaultConfig, FaultyVirtualNode, stop_all
        from arinc429.builder import WordBuilder

        print("Initializing ARINC 429 Bus Simulation...")
        bus = ArincBus()
        monitor = BusMonitor("SYSTEM_MONITOR", bus)

        adc_node = VirtualNode("ADC_1", bus)
        adc_node.register_periodic_transmission(
            lambda: WordBuilder().label(0o203).data(0x1234).build(), rate_hz=20.0
        )

        irs_node = VirtualNode("IRS_1", bus)
        irs_node.register_periodic_transmission(
            lambda: WordBuilder().label(0o310).data(0x5678).build(), rate_hz=10.0
        )

        nodes = [adc_node, irs_node]

        if args.faulty:
            fault_cfg = FaultConfig(corrupt_parity=True, drop_probability=0.1)
            faulty_node = FaultyVirtualNode("FAULTY_SENSOR", bus, fault_cfg)
            faulty_node.register_periodic_transmission(
                lambda: WordBuilder().label(0o101).data(0xFFFF).build(), rate_hz=15.0
            )
            nodes.append(faulty_node)
            print("Fault injection enabled: FAULTY_SENSOR active.")

        for n in nodes:
            n.start()

        print(f"Simulation running for {args.duration} seconds...")
        time.sleep(args.duration)

        stop_all(nodes)

        print("\n--- Simulation Summary ---")
        print(f"Total words captured on bus : {len(monitor.captured_words)}")
        print(f"Parity errors detected      : {monitor.parity_errors_detected}")
        print("Traffic Breakdown by Label:")
        for label in [0o203, 0o310, 0o101]:
            words = monitor.get_traffic_by_label(label)
            if words:
                print(f"  - Label {label:03o}: {len(words)} messages received")

    elif args.command == "replay":
        from arinc429.sim import ArincBus, BusMonitor
        from arinc429.recorder import ReplayNode

        if args.speed <= 0:
            print(f"Error: --speed must be positive, got {args.speed}")
            raise SystemExit(1)

        if args.speed <= 0:
            print(f"Error: --speed must be positive, got {args.speed}")
            raise SystemExit(1)

        print(f"Loading record file: {args.record_file}...")
        bus = ArincBus()
        monitor = BusMonitor("REPLAY_MONITOR", bus)
        
        player = ReplayNode(args.record_file, bus, speed_multiplier=args.speed)

        print("Starting playback...")
        t = threading.Thread(target=player.play, daemon=True)
        t.start()

        try:
            while t.is_alive():
                time.sleep(0.1)
        except KeyboardInterrupt:
            player.stop()

        print("\n--- Replay Summary ---")
        print(f"Total words replayed/captured: {len(monitor.captured_words)}")
        print("Replay session completed.")


if __name__ == "__main__":
    main()
