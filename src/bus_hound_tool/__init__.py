"""Utility package for monitoring USB and serial activity.

This package exposes helpers that mimic a small subset of the
capabilities of the Bus Hound analyser.  It focuses on developer
productivity features that can be exercised from a regular user space
process, such as enumerating USB devices, following hot‑plug events and
mirroring serial line traffic to structured log files.
"""

from .usb_monitor import USBMonitor
from .serial_monitor import SerialMonitor

__all__ = ["USBMonitor", "SerialMonitor"]
