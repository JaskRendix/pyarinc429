from __future__ import annotations

import argparse
import json
from pathlib import Path

from arinc429.api import combine_definitions, decode_and_validate
from arinc429.definitions import EQUIP_ADC, EQUIP_IRS, EQUIP_ALL
from arinc429.loader import Arinc615Packetizer
from arinc429.williamsburg import WilliamsburgSession
from arinc429.word import Word

EQUIP_MAP = {
    "adc": EQUIP_ADC,
    "irs": EQUIP_IRS,
    "all": EQUIP_ALL,
}


def main():
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

        decoded = {}
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
            args.output.write_text(json.dumps(hex_words, indent=2))
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
            if args.trace:
                print("RTS:", [hex(w.to_int()) for w in rts_response])

            block_words = tx.process_incoming_word(rts_response[0])
            if args.trace:
                print("BLOCK:")
                for w in block_words:
                    print(" ", hex(w.to_int()))
            
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
            print(f"\nSuccessfully reconstructed payload: {recovered.decode('utf-8')}")
        except Exception as e:
            print(f"Simulation failed with error: {e}")
            raise SystemExit(1)


if __name__ == "__main__":
    main()
