import socket
import threading
import time
from abc import ABC, abstractmethod

try:
    import serial
except ImportError:
    serial = None

from .sim import ArincBus
from .word import Word


class ArincFrameParser:
    def __init__(self) -> None:
        self._buffer: bytes = b""

    def parse(self, data: bytes) -> list[Word]:
        self._buffer += data
        words: list[Word] = []

        while len(self._buffer) >= 4:
            chunk = self._buffer[:4]
            self._buffer = self._buffer[4:]
            try:
                val = int.from_bytes(chunk, "big")
                words.append(Word.from_int(val))
            except Exception:
                pass

        return words


class ArincTransport(ABC):
    @abstractmethod
    def open(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def read(self, max_bytes: int) -> bytes:
        pass

    @abstractmethod
    def write(self, payload: bytes) -> None:
        pass


class SerialTransport(ArincTransport):
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.1) -> None:
        if serial is None:
            raise ImportError("pyserial required for SerialTransport.")
        self.port: str = port
        self.baudrate: int = baudrate
        self.timeout: float = timeout
        self.conn: Any | None = None

    def open(self) -> None:
        self.conn = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def close(self) -> None:
        if self.conn and self.conn.is_open:
            self.conn.close()

    def read(self, max_bytes: int) -> bytes:
        if self.conn and self.conn.is_open and self.conn.in_waiting:
            return self.conn.read(max_bytes)
        return b""

    def write(self, payload: bytes) -> None:
        if self.conn and self.conn.is_open:
            self.conn.write(payload)


class SocketTransport(ArincTransport):
    def __init__(
        self,
        bind_host: str,
        bind_port: int,
        remote_host: str | None = None,
        remote_port: int | None = None,
        udp: bool = True,
    ) -> None:
        self.bind_host: str = bind_host
        self.bind_port: int = bind_port
        self.remote_host: str | None = remote_host
        self.remote_port: int | None = remote_port
        self.udp: bool = udp
        self.sock: socket.socket | None = None

    def open(self) -> None:
        if self.udp:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.bind_host, self.bind_port))
            self.sock.settimeout(0.1)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(0.1)
            if self.remote_host and self.remote_port:
                self.sock.connect((self.remote_host, self.remote_port))

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def read(self, max_bytes: int) -> bytes:
        try:
            if self.sock:
                if self.udp:
                    data, _ = self.sock.recvfrom(max_bytes)
                    return data
                else:
                    return self.sock.recv(max_bytes)
        except socket.timeout:
            return b""
        except Exception:
            return b""
        return b""

    def write(self, payload: bytes) -> None:
        try:
            if self.sock:
                if self.udp:
                    if self.remote_host is None or self.remote_port is None:
                        return
                    self.sock.sendto(payload, (self.remote_host, self.remote_port))
                else:
                    self.sock.sendall(payload)
        except Exception:
            pass


class BaseArincDriver(ABC):
    def __init__(
        self,
        bus: ArincBus,
        transport: ArincTransport,
        parser: ArincFrameParser | None = None,
    ) -> None:
        self.bus: ArincBus = bus
        self.transport: ArincTransport = transport
        self.parser: ArincFrameParser = parser or ArincFrameParser()
        self.is_running: bool = False
        self._thread: threading.Thread | None = None

    def connect(self) -> None:
        self.transport.open()
        self.is_running = True
        self._thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._thread.start()

    def disconnect(self) -> None:
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self.transport.close()

    def write_word(self, word: Word) -> None:
        payload: bytes = word.raw.to_bytes(4, "big")
        self.transport.write(payload)

    def _rx_loop(self) -> None:
        while self.is_running:
            try:
                data: bytes = self.transport.read(64)
                if data:
                    for word in self.parser.parse(data):
                        self.bus.publish("HARDWARE_RX", word)
                else:
                    time.sleep(0.001)
            except Exception as e:
                self.bus.publish("DRIVER_ERROR", e)
                time.sleep(0.01)


class SerialArincDriver(BaseArincDriver):
    def __init__(self, bus: ArincBus, port: str, baudrate: int = 115200) -> None:
        transport = SerialTransport(port, baudrate)
        super().__init__(bus, transport)


class SocketArincDriver(BaseArincDriver):
    def __init__(
        self,
        bus: ArincBus,
        bind_host: str,
        bind_port: int,
        remote_host: str | None = None,
        remote_port: int | None = None,
        udp: bool = True,
    ) -> None:
        transport = SocketTransport(
            bind_host=bind_host,
            bind_port=bind_port,
            remote_host=remote_host,
            remote_port=remote_port,
            udp=udp,
        )
        super().__init__(bus, transport)
