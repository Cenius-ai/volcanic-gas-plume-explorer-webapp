#!/usr/bin/env bash
# Project-level dependency install + database seed. Never installs system packages,
# never starts the web server, always exits.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Upgrading pip tooling"
python3 -m pip install --upgrade pip setuptools wheel

echo "==> Installing project dependencies from plume/requirements.txt"
python3 -m pip install -r requirements.txt

echo "==> Creating and seeding the SQLite database"
python3 seed_data.py

echo "==> Import self-check"
python3 - <<'PY'
import sys

sys.path.insert(0, ".")
import plotly  # noqa: F401
import streamlit  # noqa: F401
import pandas  # noqa: F401

from lib import auth, db, repository, validate  # noqa: F401

print("imports ok")
PY

echo "==> Done. Start the app with:"
echo "    cd plume && python3 -m streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"
