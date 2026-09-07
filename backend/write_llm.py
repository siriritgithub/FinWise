"""Helper script to write the new llm.py in parts."""
import pathlib

LLM_PATH = pathlib.Path(r"c:\FinWise\backend\app\services\llm.py")

PART1 = '''\
"""
FinWise AI Assistant - Ollama tool-calling engine.

Architecture:
  User message
    -> Ollama/Qwen selects tool
    -> Backend safety layer validates tool choice
    -> Backend executes verified DB operation
    -> Result returned to Ollama
    -> Ollama generates natural response

The LLM never touches the database directly.
Financial truth always comes from verified backend tools.
"""

import json
import re
import threading
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Per-user pending deletion store
# {uid: {"entity": str, "id": int, "label": str, "expires": datetime}}
# ---------------------------------------------------------------------------
_pending_deletions: dict = {}
_pending_lock = threading.Lock()
DELETION_TTL_SECONDS = 120


def _set_pending_deletion(uid: int, entity: str, entity_id: int, label: str):
    with _pending_lock:
        _pending_deletions[uid] = {
            "entity": entity,
            "id": entity_id,
            "label": label,
            "expires": datetime.utcnow() + timedelta(seconds=DELETION_TTL_SECONDS),
        }


def _get_pending_deletion(uid: int):
    with _pending_lock:
        p = _pending_deletions.get(uid)
        if p and datetime.utcnow() < p["expires"]:
            return p
        _pending_deletions.pop(uid, None)
        return None


def _clear_pending_deletion(uid: int):
    with _pending_lock:
        _pending_deletions.pop(uid, None)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(amount) -> str:
    """Format a number as Indian rupee string."""
    try:
        v = float(amount or 0)
    except Exception:
        v = 0.0
    return f"\u20b9{v:,.2f}"


def _clean(text: str) -> str:
    """Remove broken markdown and raw labels from LLM output."""
    if not text:
        return text
    # Remove markdown bold/italic/headers/code fences
    text = re.sub(r"\*\*(.+?)\*\*", r"\\1", text)
    text = re.sub(r"\*(.+?)\*", r"\\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"```[\\s\\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\\1", text)
    # Replace INR label with rupee symbol
    text = re.sub(r"\\bINR\\s*", "\u20b9", text)
    text = re.sub(r"\\bRs\\.?\\s*", "\u20b9", text)
    # Collapse excessive blank lines
    text = re.sub(r"\\n{3,}", "\\n\\n", text)
    return text.strip()

'''

LLM_PATH.write_text(PART1, encoding="utf-8")
print("part1 ok", len(PART1))
