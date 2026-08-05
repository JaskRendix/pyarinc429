from __future__ import annotations

import asyncio
from typing import Final

from arinc429.sim import ArincBus
from arinc429.transport import AsyncBusTransportDriver


class DummyTransport:
    def open(self) -> None:
        print("Transport opened.")

    def close(self) -> None:
        print("Transport closed.")

    def write(self, data: bytes) -> None:
        print(f"TX {data.hex()}")

    def read(self, size: int) -> bytes:
        return b""


async def main() -> None:
    bus: ArincBus = ArincBus()
    transport: DummyTransport = DummyTransport()

    driver: AsyncBusTransportDriver = AsyncBusTransportDriver(
        bus=bus,
        transport=transport,
        source_id="EXT_DEVICE",
    )

    await driver.connect()
    print("Driver active.")

    try:
        await asyncio.sleep(5)
    finally:
        await driver.disconnect()
        print("Driver stopped.")


if __name__ == "__main__":
    asyncio.run(main())
