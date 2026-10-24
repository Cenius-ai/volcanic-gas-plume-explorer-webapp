"""SO2 flux by crater vent page."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.page_setup import bootstrap  # noqa: E402
from views import flux  # noqa: E402

bootstrap("SO2 flux by vent")
flux.render()
