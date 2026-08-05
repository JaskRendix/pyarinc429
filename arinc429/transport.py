from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable

from .drivers import ArincFrameParser
from .sim import ArincBus, BusListener
from .word import Word


class AsyncBusTransportDriver(BusListener):

    def __init__(
        self,
        bus: ArincBus,
        transport: Any,
        source_id: str = "HW_DEVICE",
        error_callback: Callable[[Exception, str], None] | None = None
    ) -> None:
        self.bus = bus
        self.transport = transport
        self.parser = ArincFrameParser()
        self.source_id = source_id
        self.error_callback = error_callback

        self._task: asyncio.Task[None] | None = None
        self._running = False

        self.bus.attach(self)

    async def connect(self) -> None:
        self.transport.open()
        self._running = True
        self._task = asyncio.create_task(self._rx_loop())

    async def disconnect(self) -> None:
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.transport.close()

    def on_word_received(self, word: Word, source_id: str) -> None:
        if source_id == self.source_id:
            return

        try:
            payload = word.raw.to_bytes(4, "big")
            self.transport.write(payload)
        except Exception as e:
            if self.error_callback:
                self.error_callback(e, self.source_id)

    async def _rx_loop(self) -> None:
        while self._running:
            try:
                data = self.transport.read(64)

                if data:
                    for word in self.parser.parse(data):
                        self.bus.transmit(word, self.source_id)
                else:
                    await asyncio.sleep(0.001)

            except Exception as e:
                if self.error_callback:
                    self.error_callback(e, self.source_id)
                await asyncio.sleep(0.01)
