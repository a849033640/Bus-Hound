"""USB monitoring utilities for Windows hosts.

The monitor offered in this module is intentionally lightweight – it does
not require kernel level drivers and therefore cannot access the raw bus
packets that specialised analysers such as Bus Hound capture.  Instead it
focuses on functionality that is useful for application developers: it
tracks hot‑plug events, enumerates connected devices and exports a stream
of structured log messages describing what is connected to the host.

Only Windows is supported.  The implementation polls :mod:`pyusb` on a
configurable interval which makes the monitor easy to run without having
to integrate with Win32 message pumps.  The polling approach works well on
modern Windows installations as long as the libusb driver is installed for
the device classes that need to be observed.

The monitor integrates with :mod:`asyncio` so that it can be combined with
other asynchronous workloads.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import json
import sys
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, Optional


def _utc_timestamp() -> str:
    """Return an ISO 8601 timestamp in UTC with a ``Z`` suffix."""

    return _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class USBDevice:
    """Representation of a USB device.

    Only a curated subset of the full USB descriptor tree is collected.
    This keeps the monitor portable and limits the amount of privileged
    access required to gather information.
    """

    vendor_id: str
    product_id: str
    bus: Optional[str] = None
    address: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    serial_number: Optional[str] = None

    @classmethod
    def from_usb_device(cls, device: "usb.core.Device") -> "USBDevice":
        """Create a :class:`USBDevice` from a :mod:`pyusb` device object."""

        # Pulling the descriptors can raise USBError when permission is
        # denied.  They are therefore requested defensively and the
        # monitor simply omits the information if unavailable.
        def _safe_get(attr: str) -> Optional[str]:
            try:
                value = getattr(device, attr, None)
            except Exception:  # pragma: no cover - defensive
                return None
            if value is None:
                return None
            try:
                return str(value)
            except Exception:  # pragma: no cover - defensive
                return None

        busnum = getattr(device, "bus", None)
        address = getattr(device, "address", None)
        return cls(
            vendor_id=f"0x{int(device.idVendor):04x}",
            product_id=f"0x{int(device.idProduct):04x}",
            bus=str(busnum) if busnum is not None else None,
            address=str(address) if address is not None else None,
            manufacturer=_safe_get("manufacturer"),
            product=_safe_get("product"),
            serial_number=_safe_get("serial_number"),
        )


@dataclass(frozen=True)
class USBEvent:
    """Structured event emitted by :class:`USBMonitor`."""

    action: str
    timestamp: str
    device: USBDevice

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class USBMonitor:
    """Asynchronous monitor that produces :class:`USBEvent` objects.

    Windows is the only supported platform.  The monitor relies on periodic
    polling of :mod:`pyusb` to detect attachments and detachments.
    """

    def __init__(
        self,
        *,
        poll_interval: float = 2.0,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        output = None,
    ) -> None:
        self.poll_interval = poll_interval
        self._loop = loop
        self._output = output or sys.stdout
        self._stop_event = asyncio.Event()
        self._known_devices: Dict[str, USBDevice] = {}

    def stop(self) -> None:
        """Request the monitor to stop."""

        self._stop_event.set()

    async def run(self) -> None:
        """Start monitoring USB events until :meth:`stop` is called."""

        loop = self._loop or asyncio.get_running_loop()
        self._stop_event.clear()
        if sys.platform != "win32":  # pragma: no cover - safety guard
            raise RuntimeError("USBMonitor only supports Windows hosts")

        await self._run_with_polling()

    async def _run_with_polling(self) -> None:
        while not self._stop_event.is_set():
            current_devices = {dev.vendor_id + dev.product_id + (dev.address or ""): dev for dev in self._enumerate_devices()}

            # Detect attachments
            for key, device in current_devices.items():
                if key not in self._known_devices:
                    event = USBEvent(
                        action="attach",
                        timestamp=_utc_timestamp(),
                        device=device,
                    )
                    self._emit_event(event)

            # Detect detachments
            for key, device in list(self._known_devices.items()):
                if key not in current_devices:
                    event = USBEvent(
                        action="detach",
                        timestamp=_utc_timestamp(),
                        device=device,
                    )
                    self._emit_event(event)

            self._known_devices = current_devices
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                continue

    def _emit_event(self, event: USBEvent) -> None:
        if hasattr(self._output, "write"):
            self._output.write(event.to_json() + "\n")
            self._output.flush()
        else:  # pragma: no cover - fallback for custom writers
            self._output(event)

    # ------------------------------------------------------------------
    def _enumerate_devices(self) -> Iterable[USBDevice]:
        try:
            import usb.core  # type: ignore
        except Exception:
            return []

        try:
            devices = usb.core.find(find_all=True)
        except Exception:
            return []

        result = []
        for device in devices or []:
            try:
                result.append(USBDevice.from_usb_device(device))
            except Exception:
                continue
        return result

__all__ = ["USBDevice", "USBEvent", "USBMonitor"]
