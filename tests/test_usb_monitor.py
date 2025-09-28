import asyncio
import io
import json

import pytest

from bus_hound_tool.usb_monitor import USBDevice, USBMonitor


def test_polling_emits_attach_and_detach(monkeypatch):
    output = io.StringIO()
    monitor = USBMonitor(poll_interval=0.01, output=output)

    device = USBDevice(vendor_id="0x1111", product_id="0x2222", address="1")
    sequence = [[device], []]

    call_count = 0

    def fake_enumerate():
        nonlocal call_count
        index = min(call_count, len(sequence) - 1)
        call_count += 1
        return sequence[index]

    monkeypatch.setattr("bus_hound_tool.usb_monitor.sys.platform", "win32")
    monkeypatch.setattr(monitor, "_enumerate_devices", fake_enumerate)

    async def runner():
        async def stop_later():
            await asyncio.sleep(0.05)
            monitor.stop()

        await asyncio.gather(monitor.run(), stop_later())

    asyncio.run(runner())

    lines = [json.loads(line) for line in output.getvalue().splitlines() if line.strip()]
    actions = [event["action"] for event in lines]

    assert actions == ["attach", "detach"]
    assert lines[0]["device"]["vendor_id"] == "0x1111"
    assert lines[1]["device"]["address"] == "1"


def test_windows_only_guard(monkeypatch):
    output = io.StringIO()
    monitor = USBMonitor(poll_interval=0.01, output=output)
    monkeypatch.setattr("bus_hound_tool.usb_monitor.sys.platform", "linux")

    async def runner():
        await monitor.run()

    with pytest.raises(RuntimeError):
        asyncio.run(runner())
