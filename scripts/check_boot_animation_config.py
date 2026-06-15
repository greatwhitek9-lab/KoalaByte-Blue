#!/usr/bin/env python3
"""Compatibility wrapper for the current KoalaByte Blue readiness check.

The original script name is kept so older docs, CI jobs, and local workflows do
not break. New automation should call scripts/check_repo_readiness.py directly.
"""

from __future__ import annotations

from check_repo_readiness import main


if __name__ == "__main__":
    raise SystemExit(main())
