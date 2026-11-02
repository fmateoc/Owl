"""Process identity: is a PID alive, and which process is it (S9).

A bare PID can be reused, so every kill is checked against the process start token the
worker recorded in `status.json` (`pid_started`). Windows: OpenProcess/GetProcessTimes.
POSIX: `kill(pid, 0)` and Linux's /proc start time. Where a token cannot be read, the
manager cancels cooperatively only and never kills.
"""

from __future__ import annotations

import os
from typing import Optional


def pid_alive(pid) -> bool:
    """True when a process with this PID exists (access denied means it exists)."""
    if pid is None:
        return False
    pid = int(pid)
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        ERROR_ACCESS_DENIED = 5
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.GetLastError() == ERROR_ACCESS_DENIED
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_start_token(pid) -> Optional[int]:
    """The process's start time as an opaque token; None where it cannot be read.

    Windows: the creation time from GetProcessTimes. POSIX: Linux's /proc start time
    (clock ticks since boot); None elsewhere or when the process is gone.
    """
    if pid is None:
        return None
    pid = int(pid)
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            creation, exit_t, kernel_t, user_t = (wintypes.FILETIME() for _ in range(4))
            if not kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_t),
                                            ctypes.byref(kernel_t), ctypes.byref(user_t)):
                return None
            return (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        finally:
            kernel32.CloseHandle(handle)
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            # Field 22 is the start time in clock ticks since boot (comm can hold spaces).
            return int(f.read().rsplit(")", 1)[1].split()[19])
    except OSError:
        return None


def kill_process(pid, start_token=None) -> bool:
    """Kill a process, but only when it is the one that started at `start_token` (S9).

    With no token to check (None on both sides is not enough: an unknown token refuses),
    the kill is refused: cancel cooperatively instead. Returns True when killed.
    """
    if pid is None:
        return False
    if start_token is None or process_start_token(pid) != start_token:
        return False
    pid = int(pid)
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if not handle:
            return False
        try:
            return bool(kernel32.TerminateProcess(handle, 1))
        finally:
            kernel32.CloseHandle(handle)
    import signal

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return False
    return True
