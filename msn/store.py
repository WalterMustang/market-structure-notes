#!/usr/bin/env python3
"""
Market Structure Notes - Metadata Store (v0.1)

Simple, local JSON-based metadata layer.
Notes themselves remain as .md files. This store only holds structured data:
status, P&L, tags, etc.

Design goals:
- Backward compatible with existing notes
- No external dependencies
- Simple and auditable
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).parent.parent
NOTES_DIR = ROOT / "notes"
STORE_FILE = NOTES_DIR / ".msn.json"


def ensure_notes_dir():
    NOTES_DIR.mkdir(exist_ok=True)


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _default_meta(note_id: str, symbol: str = "", timeframe: str = "", template: str = "") -> Dict[str, Any]:
    return {
        "id": note_id,
        "status": "idea",
        "symbol": symbol.upper() if symbol else "",
        "timeframe": timeframe.upper() if timeframe else "",
        "template": template,
        "pnl": {
            "entry": None,
            "exit": None,
            "rr": None,
            "result": None,   # win / loss / breakeven
        },
        "tags": [],
        "created_at": _now(),
        "updated_at": _now(),
    }


def load_store() -> Dict[str, Any]:
    ensure_notes_dir()
    if not STORE_FILE.exists():
        return {"version": 1, "notes": {}}

    try:
        data = json.loads(STORE_FILE.read_text())
        if "version" not in data:
            data["version"] = 1
        if "notes" not in data:
            data["notes"] = {}
        return data
    except Exception:
        # Corrupt file — start fresh but don't delete user notes
        return {"version": 1, "notes": {}}


def save_store(data: Dict[str, Any]) -> None:
    ensure_notes_dir()
    STORE_FILE.write_text(json.dumps(data, indent=2))


def _migrate_existing_notes(store: Dict[str, Any]) -> int:
    """Auto-create minimal metadata for any .md files that don't have records yet."""
    migrated = 0
    for md_file in NOTES_DIR.glob("*.md"):
        note_id = md_file.stem
        if note_id in store["notes"]:
            continue

        # Try to extract basic info from the markdown content
        content = md_file.read_text()
        lines = content.splitlines()
        symbol = ""
        timeframe = ""
        template = ""

        # Detect template from title (first heading)
        first_line = lines[0].lower() if lines else ""
        if "wyckoff" in first_line:
            template = "wyckoff"
        elif "smc" in first_line or "ict" in first_line:
            template = "smc"
        elif "price action" in first_line:
            template = "price-action"
        elif "volume" in first_line:
            template = "volume-profile"
        elif "macro" in first_line:
            template = "macro"
        elif "session" in first_line:
            template = "session"
        else:
            template = "minimal"

        # Very simple extraction for symbol/timeframe
        for line in lines:
            if line.lower().startswith("symbol:"):
                symbol = line.split(":", 1)[1].strip()
            if line.lower().startswith("timeframe:"):
                timeframe = line.split(":", 1)[1].strip()

        meta = _default_meta(note_id, symbol, timeframe, template)
        store["notes"][note_id] = meta
        migrated += 1

    if migrated > 0:
        save_store(store)
    return migrated


def get_note_meta(note_id: str) -> Optional[Dict[str, Any]]:
    store = load_store()
    _migrate_existing_notes(store)
    return store["notes"].get(note_id)


def set_note_meta(note_id: str, **updates) -> Dict[str, Any]:
    store = load_store()
    _migrate_existing_notes(store)

    if note_id not in store["notes"]:
        # Create minimal record
        store["notes"][note_id] = _default_meta(note_id)

    meta = store["notes"][note_id]
    for key, value in updates.items():
        if key == "pnl" and isinstance(value, dict):
            meta["pnl"].update(value)
        elif key in meta:
            meta[key] = value

    meta["updated_at"] = _now()
    save_store(store)
    return meta


def list_notes_meta(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    template: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[Dict[str, Any]]:
    store = load_store()
    _migrate_existing_notes(store)

    results = []
    for meta in store["notes"].values():
        if status and meta.get("status") != status:
            continue
        if symbol and meta.get("symbol", "").upper() != symbol.upper():
            continue
        if template and meta.get("template") != template:
            continue
        if tag and tag not in meta.get("tags", []):
            continue
        results.append(meta)

    # Sort by updated_at desc
    results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return results


def get_stats() -> Dict[str, Any]:
    store = load_store()
    _migrate_existing_notes(store)

    notes = list(store["notes"].values())
    total = len(notes)

    by_status: Dict[str, int] = {}
    by_symbol: Dict[str, int] = {}
    by_template: Dict[str, int] = {}

    closed = 0
    wins = 0
    losses = 0

    for n in notes:
        s = n.get("status", "idea")
        by_status[s] = by_status.get(s, 0) + 1

        sym = n.get("symbol", "").upper()
        if sym:
            by_symbol[sym] = by_symbol.get(sym, 0) + 1

        tpl = n.get("template", "")
        if tpl:
            by_template[tpl] = by_template.get(tpl, 0) + 1

        if s == "closed":
            closed += 1
            result = n.get("pnl", {}).get("result")
            if result == "win":
                wins += 1
            elif result == "loss":
                losses += 1

    win_rate = round((wins / closed * 100), 1) if closed > 0 else 0.0

    return {
        "total_notes": total,
        "by_status": by_status,
        "by_symbol": by_symbol,
        "by_template": by_template,
        "closed_notes": closed,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
    }


def update_pnl(note_id: str, entry: Any = None, exit: Any = None, rr: Any = None, result: Optional[str] = None) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    if entry is not None:
        updates["entry"] = entry
    if exit is not None:
        updates["exit"] = exit
    if rr is not None:
        updates["rr"] = rr
    if result is not None:
        updates["result"] = result

    return set_note_meta(note_id, pnl=updates)


def set_status(note_id: str, status: str) -> Dict[str, Any]:
    valid = {"idea", "paper", "closed"}
    if status not in valid:
        raise ValueError(f"Invalid status. Must be one of: {valid}")
    return set_note_meta(note_id, status=status)


def add_tag(note_id: str, tag: str) -> Dict[str, Any]:
    store = load_store()
    _migrate_existing_notes(store)
    meta = store["notes"].get(note_id)
    if not meta:
        meta = _default_meta(note_id)
        store["notes"][note_id] = meta

    if tag not in meta["tags"]:
        meta["tags"].append(tag)
    meta["updated_at"] = _now()
    save_store(store)
    return meta


# Convenience: get all note ids that have .md files
def get_all_note_ids() -> List[str]:
    ensure_notes_dir()
    return sorted([p.stem for p in NOTES_DIR.glob("*.md")], reverse=True)