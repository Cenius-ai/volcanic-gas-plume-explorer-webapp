# Install and run the Plume Explorer

Everything below runs on the standard CPython 3.11 interpreter. There is no virtualenv
requirement, no system package to install and no external service to start.

## 1. Install dependencies

```bash
bash plume/install.sh
```

That script upgrades pip tooling, installs `plume/requirements.txt`, creates
`plume/plume.db` and seeds it, then exits. It is safe to run again: the seed is idempotent and
reports the row counts it found.

Manual equivalent:

```bash
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r plume/requirements.txt
```

## 2. Seed the database

```bash
python3 plume/seed_data.py
```

Creates the schema if needed and fills it with 6 crater vents, 276 SO2 flux traverses, 2 884
tremor samples across 4 stations, 6 fumarole notes, 4 alert episodes (one per level) and two
accounts. Prints the row counts and the reference date. This step never starts a web server.

Timestamps are not taken from the wall clock: the whole 90-day series is derived from the
constant `REFERENCE_DATE` (2026-10-24 09:00 UTC) in `plume/seed_data.py`, and the page windows
are measured back from that stored date. Charts are therefore complete the moment the app
opens, on any machine, on any day.

## 3. Run the app

```bash
cd plume
python3 -m streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

Open <http://localhost:8501>. The entry script is `plume/streamlit_app.py`; the feature pages
sit in `plume/pages/` and appear in the sidebar navigation.

The app also creates and seeds the database on its own boot path (`ensure_seeded()` in
`plume/seed_data.py`), so step 2 is only needed when you want to see the seeding report.

## 4. Run the tests

```bash
python3 plume/run_tests.py
# or
python3 -m pytest plume/tests -q
```

Tests use a throwaway SQLite file per test (`PLUME_DB_PATH`) and a fixed reference date, so
they never touch `plume/plume.db` and never depend on the wall clock.

## Environment variables

Both are optional; the app boots with neither set.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PLUME_DB_PATH` | `plume/plume.db` | Override the SQLite file location (used by the tests) |
| `PLUME_SESSION_SECRET` | development key in `lib/auth.py` | HMAC key for the signed reload token; set a real value in production |

## Troubleshooting

- **"Address already in use"** — another Streamlit process is holding 8501. Stop it; the seed
  script never binds a port.
- **Empty screens** — the database exists but has no rows: run `python3 plume/seed_data.py`.
- **Sign-in rejected** — the seed writes the demo account through the same hashing path the
  login verifies; if the account was removed, re-run the seed (`cenius@cenius.ai` / `cenius`).
- **Fonts look like system defaults** — static file serving is enabled in
  `plume/.streamlit/config.toml`; if it is disabled the app falls back to the system font
  stack and everything else still works.
