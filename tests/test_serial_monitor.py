import asyncio
import io
import json

from bus_hound_tool.serial_monitor import SerialMonitor


class DummySerial:
    def __init__(self):
        self._reads = [b"ABC", b"", b"\x01\x02"]
        self.closed = False

    def read(self, _: int):
        if self._reads:
            return self._reads.pop(0)
        return b""

    def close(self):
        self.closed = True


def test_serial_monitor_logs_hex_payload():
    output = io.StringIO()

    monitor = SerialMonitor(
        "loop://",
        serial_factory=DummySerial,
        output=output,
        chunk_size=3,
    )

    async def runner():
        async def stop_later():
            await asyncio.sleep(0.05)
            monitor.stop()

        await asyncio.gather(monitor.run(), stop_later())

    asyncio.run(runner())

    lines = [json.loads(line) for line in output.getvalue().splitlines() if line.strip()]
    assert lines
    assert lines[0]["payload"] == "414243"
