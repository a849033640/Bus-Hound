"""Serial monitoring utilities."""
from __future__ import annotations

import asyncio
import contextlib
import datetime as _dt
import json
import sys
from dataclasses import dataclass, asdict
from typing import Callable, Optional


def _utc_timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SerialEvent:
    """Structured serial line event."""

    timestamp: str
    direction: str
    payload: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class SerialMonitor:
    """Mirror traffic on a serial port to JSON formatted log entries.

    The monitor is intentionally designed to be testable: a custom
    ``serial_factory`` can be supplied so that unit tests can feed bytes to
    the monitor without touching real hardware.
    """

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 115200,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: float = 0.1,
        chunk_size: int = 1024,
        serial_factory: Optional[Callable[[], "serial.SerialBase"]] = None,
        output=None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.serial_factory = serial_factory
        self._output = output or sys.stdout
        self._stop_event = asyncio.Event()
        self._serial = None

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        self._stop_event.clear()
        if self.serial_factory is not None:
            serial_obj = self.serial_factory()
        else:
            serial_obj = self._open_serial()
        self._serial = serial_obj
        try:
            while not self._stop_event.is_set():
                data = await asyncio.to_thread(serial_obj.read, self.chunk_size)
                if data:
                    self._emit_event(
                        SerialEvent(
                            timestamp=_utc_timestamp(),
                            direction="in",
                            payload=data.hex(),
                        )
                    )
                else:
                    await asyncio.sleep(self.timeout)
        finally:
            with contextlib.suppress(Exception):
                serial_obj.close()

    def _open_serial(self):
        import serial  # type: ignore

        return serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=self.bytesize,
            parity=self.parity,
            stopbits=self.stopbits,
            timeout=self.timeout,
        )

    def _emit_event(self, event: SerialEvent) -> None:
        if hasattr(self._output, "write"):
            self._output.write(event.to_json() + "\n")
            self._output.flush()
        else:  # pragma: no cover - fallback for custom writers
            self._output(event)


__all__ = ["SerialEvent", "SerialMonitor"]
