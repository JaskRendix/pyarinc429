from __future__ import annotations

import json
import time
from pathlib import Path

from .sim import ArincBus
from .word import Word


class BusRecorder:

    @staticmethod
    def export_to_jsonl(
        captured_words: list[tuple[float, Word, str]], filepath: Path | str
    ) -> None:
        path = Path(filepath)
        with path.open("w", encoding="utf-8") as f:
            for timestamp, word, source_id in captured_words:
                record = {
                    "timestamp": timestamp,
                    "word_int": word.to_int(),
                    "parity_type": word.parity_type,
                    "source_id": source_id,
                }
                f.write(json.dumps(record) + "\n")


class ReplayNode:

    def __init__(
        self, filepath: Path | str, bus: ArincBus, speed_multiplier: float = 1.0
    ) -> None:
        self.filepath = Path(filepath)
        self.bus = bus
        self.speed_multiplier = speed_multiplier
        self._running = False

    def play(self) -> None:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Record file not found: {self.filepath}")

        with self.filepath.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return

        self._running = True
        records = [json.loads(line) for line in lines]

        start_real_time = time.time()
        start_log_time = records[0]["timestamp"]

        for rec in records:
            if not self._running:
                break

            log_delta = rec["timestamp"] - start_log_time
            target_real_delay = log_delta / self.speed_multiplier

            elapsed_real = time.time() - start_real_time
            sleep_time = target_real_delay - elapsed_real

            if sleep_time > 0:
                time.sleep(sleep_time)

            word = Word.from_int(rec["word_int"], rec["parity_type"])
            self.bus.publish(word, source_id=f"REPLAY:{rec['source_id']}")

    def stop(self) -> None:
        self._running = False
