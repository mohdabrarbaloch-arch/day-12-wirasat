"""Vercel serverless entry point.

Wirasat normally runs with SQLite/Postgres; on Vercel we use a writable
/tmp SQLite file since the filesystem is ephemeral. Data persists for the
life of the serverless instance only — fine for a demo, use Postgres
(Neon/Supabase) for production persistence.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/wirasat.db")

# Ensure the app package is importable on Vercel's python runtime.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

handler = app
