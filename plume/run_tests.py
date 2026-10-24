"""Run the Plume Explorer test suite: python3 plume/run_tests.py"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLUME_DIR = Path(__file__).resolve().parent
TESTS_DIR = PLUME_DIR / "tests"


def main() -> int:
    sys.path.insert(0, str(PLUME_DIR))
    return pytest.main([str(TESTS_DIR), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
