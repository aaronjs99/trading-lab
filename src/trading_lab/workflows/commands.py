from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys


@dataclass(frozen=True)
class CommandResult:
    name: str
    returncode: int


class CommandRunner:
    """Small wrapper around subprocess for visible, fail-fast workflows."""

    def run(self, name: str, command: list[str]) -> CommandResult:
        print()
        print(f"== {name} ==")
        completed = subprocess.run(command, check=False)

        if completed.returncode != 0:
            raise SystemExit(f"{name} failed with code {completed.returncode}")

        return CommandResult(name=name, returncode=completed.returncode)


def py(script: str, *args: str) -> list[str]:
    return [sys.executable, script, *args]
