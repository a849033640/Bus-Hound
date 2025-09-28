"""Command line interface for the lightweight Bus Hound clone."""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys
from typing import Iterable, Optional

from .serial_monitor import SerialMonitor
from .usb_monitor import USBMonitor


def _open_output(path: Optional[str]):
    if not path:
        return sys.stdout
    file_path = pathlib.Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path.open("a", encoding="utf-8")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bus-hound-lite",
        description=(
            "Monitor USB hot-plug events and serial line traffic on Windows"
            " hosts from the command line."
        ),
    )
    parser.add_argument(
        "--log-file",
        help="Write JSON events to the specified file instead of stdout.",
    )
    parser.add_argument(
        "--usb",
        action="store_true",
        help="Enable USB hot-plug monitoring.",
    )
    parser.add_argument(
        "--serial",
        metavar="PORT",
        help="Enable serial monitoring on the given port (e.g. COM3).",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Baud rate to use when opening the serial port (default: 115200).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval used by the USB monitor (default: 2.0s).",
    )
    return parser


async def _run_monitors(args: argparse.Namespace) -> None:
    output = _open_output(args.log_file)
    tasks = []
    try:
        if args.usb:
            usb_monitor = USBMonitor(poll_interval=args.poll_interval, output=output)
            tasks.append(asyncio.create_task(usb_monitor.run()))

        if args.serial:
            serial_monitor = SerialMonitor(
                args.serial,
                baudrate=args.baudrate,
                output=output,
            )
            tasks.append(asyncio.create_task(serial_monitor.run()))

        if not tasks:
            raise SystemExit("No monitor selected. Use --usb and/or --serial.")

        await asyncio.gather(*tasks)
    finally:
        if output is not sys.stdout:
            output.close()


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        asyncio.run(_run_monitors(args))
    except KeyboardInterrupt:
        return 1
    except Exception as exc:  # pragma: no cover - top level safety net
        parser.error(str(exc))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
