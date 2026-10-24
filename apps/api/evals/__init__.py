"""Deterministic, text-mode evals for the voice receptionist.

The suite drives the real HMAC-signed tool endpoints against a real PostgreSQL test database.
The scripted agent mirrors the worker's tool policy; no provider key or audio pipeline is needed,
so the same suite runs in CI. See `python -m evals --help`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_AGENT_SRC = Path(__file__).resolve().parents[2] / "agent" / "src"
if str(_AGENT_SRC) not in sys.path:
    sys.path.insert(0, str(_AGENT_SRC))
