"""Background localhost service for the portfolio GUI.

This module is intentionally local-only:
- binds to 127.0.0.1
- stores PID/log files under gitignored data/runtime
- never talks to a broker
- never places orders
"""

from __future__ import annotations

import argparse
import os
import platform
import signal
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.error import URLError
from urllib.request import urlopen


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 811
RUNTIME_DIR = Path("data/runtime")
PID_FILE = RUNTIME_DIR / "tl_gui.pid"
LOG_FILE = RUNTIME_DIR / "tl_gui.log"


@dataclass(frozen=True)
class ServiceStatus:
    running: bool
    pid: int | None
    url: str
    pid_file: Path
    log_file: Path


def service_url(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    return f"http://{host}:{port}/"


def _read_pid(pid_file: Path = PID_FILE) -> int | None:
    try:
        text = pid_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _server_responds(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    try:
        with urlopen(service_url(host, port), timeout=1.5) as response:
            return 200 <= int(response.status) < 500
    except (OSError, URLError, TimeoutError):
        return False


def status(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ServiceStatus:
    pid = _read_pid()
    running = bool(pid and _pid_is_running(pid)) or _server_responds(host, port)
    return ServiceStatus(
        running=running,
        pid=pid,
        url=service_url(host, port),
        pid_file=PID_FILE,
        log_file=LOG_FILE,
    )


def _creationflags_for_windows() -> int:
    if platform.system().lower() != "windows":
        return 0
    flags = 0
    for name in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS"):
        flags |= int(getattr(subprocess, name, 0))
    return flags


def _popen_kwargs(log_file):
    system = platform.system().lower()
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
        "cwd": str(Path.cwd()),
    }
    if system == "windows":
        kwargs["creationflags"] = _creationflags_for_windows()
    else:
        kwargs["start_new_session"] = True
    return kwargs


def start(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    open_browser: bool = True,
    force: bool = False,
) -> ServiceStatus:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    current = status(host, port)
    if current.running and not force:
        if open_browser:
            webbrowser.open(current.url)
        return current

    if current.pid and force:
        stop(host, port)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_handle = LOG_FILE.open("a", encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "trading_lab.portfolio.service",
        "serve",
        "--host",
        host,
        "--port",
        str(port),
    ]

    process = subprocess.Popen(cmd, **_popen_kwargs(log_handle))
    PID_FILE.write_text(str(process.pid), encoding="utf-8")

    # Give the server a short moment to bind.
    for _ in range(25):
        if _server_responds(host, port):
            break
        time.sleep(0.2)

    final = status(host, port)
    if open_browser:
        webbrowser.open(final.url)
    return final


def stop(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ServiceStatus:
    pid = _read_pid()
    if pid and _pid_is_running(pid):
        try:
            if platform.system().lower() == "windows":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    if PID_FILE.exists():
        PID_FILE.unlink()

    # Give the OS a moment to release the port.
    time.sleep(0.5)
    return status(host, port)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    # Import lazily so normal CLI startup stays fast.
    from trading_lab.portfolio.gui import run_gui

    run_gui(host=host, port=port, open_browser=False)


def print_status(state: ServiceStatus) -> None:
    if state.running:
        pid_text = str(state.pid) if state.pid else "unknown"
        print(f"tl GUI service: RUNNING")
        print(f"URL: {state.url}")
        print(f"PID: {pid_text}")
        print(f"Log: {state.log_file}")
    else:
        print("tl GUI service: STOPPED")
        print(f"URL: {state.url}")
        print(f"PID file: {state.pid_file}")
        print(f"Log: {state.log_file}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage the trading-lab portfolio GUI service.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("start", "stop", "status", "serve"):
        p = sub.add_parser(name)
        p.add_argument("--host", default=DEFAULT_HOST)
        p.add_argument("--port", type=int, default=DEFAULT_PORT)

    sub.choices["start"].add_argument("--no-open", action="store_true")
    sub.choices["start"].add_argument("--force", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "start":
        print_status(start(args.host, args.port, open_browser=not args.no_open, force=args.force))
        return 0
    if args.cmd == "stop":
        print_status(stop(args.host, args.port))
        return 0
    if args.cmd == "status":
        print_status(status(args.host, args.port))
        return 0
    if args.cmd == "serve":
        serve(args.host, args.port)
        return 0

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
