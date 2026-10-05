#!/usr/bin/env python3
"""Safe Alembic upgrade wrapper for local and production.

Runs `alembic upgrade head` after printing current/head state.
Idempotent migrations mean re-running is safe when schema already matches.
"""
from __future__ import annotations

import subprocess
import sys


def _run(args: list[str]) -> int:
    print("+", " ".join(args), flush=True)
    completed = subprocess.run(args)
    return completed.returncode


def main() -> int:
    print("=== Alembic status (before) ===", flush=True)
    _run([sys.executable, "-m", "alembic", "current"])
    _run([sys.executable, "-m", "alembic", "heads"])

    print("=== alembic upgrade head ===", flush=True)
    code = _run([sys.executable, "-m", "alembic", "upgrade", "head"])
    if code != 0:
        print("Migration failed.", flush=True)
        return code

    print("=== Alembic status (after) ===", flush=True)
    _run([sys.executable, "-m", "alembic", "current"])
    print("Migrations OK.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
