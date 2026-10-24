"""Eruption alert episodes page."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.page_setup import bootstrap  # noqa: E402
from views import alerts  # noqa: E402

bootstrap("Alert episodes")
alerts.render()
