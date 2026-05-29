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
    """
    Rich analytics for review (v0.2 direction).

    Returns:
    - counts by status/symbol/template
    - closed trade performance (overall + broken down by template and by symbol)
    - average R:R on closed trades (where R:R was recorded)
    """
    store = load_store()
    _migrate_existing_notes(store)

    notes = list(store["notes"].values())
    total = len(notes)

    by_status: Dict[str, int] = {}
    by_symbol: Dict[str, int] = {}
    by_template: Dict[str, int] = {}

    closed_notes = 0
    paper_notes = 0

    # Overall closed performance
    wins = 0
    losses = 0
    breakevens = 0
    rr_values: List[float] = []

    # Per-template performance (only closed)
    template_perf: Dict[str, Dict[str, Any]] = {}
    # Per-symbol performance (only closed)
    symbol_perf: Dict[str, Dict[str, Any]] = {}

    for n in notes:
        s = n.get("status", "idea")
        by_status[s] = by_status.get(s, 0) + 1

        if s == "paper":
            paper_notes += 1

        sym = n.get("symbol", "").upper()
        if sym:
            by_symbol[sym] = by_symbol.get(sym, 0) + 1

        tpl = n.get("template", "") or "unknown"
        if tpl:
            by_template[tpl] = by_template.get(tpl, 0) + 1

        # Only analyze closed trades for performance
        if s == "closed":
            closed_notes += 1
            pnl = n.get("pnl", {}) or {}
            result = pnl.get("result")
            rr = pnl.get("rr")

            if result == "win":
                wins += 1
            elif result == "loss":
                losses += 1
            elif result == "breakeven":
                breakevens += 1

            if isinstance(rr, (int, float)):
                rr_values.append(float(rr))

            # Template performance
            if tpl not in template_perf:
                template_perf[tpl] = {"closed": 0, "wins": 0, "losses": 0, "breakevens": 0, "rrs": []}
            template_perf[tpl]["closed"] += 1
            if result == "win":
                template_perf[tpl]["wins"] += 1
            elif result == "loss":
                template_perf[tpl]["losses"] += 1
            elif result == "breakeven":
                template_perf[tpl]["breakevens"] += 1
            if isinstance(rr, (int, float)):
                template_perf[tpl]["rrs"].append(float(rr))

            # Symbol performance
            if sym and sym not in symbol_perf:
                symbol_perf[sym] = {"closed": 0, "wins": 0, "losses": 0, "breakevens": 0, "rrs": []}
            if sym:
                symbol_perf[sym]["closed"] += 1
                if result == "win":
                    symbol_perf[sym]["wins"] += 1
                elif result == "loss":
                    symbol_perf[sym]["losses"] += 1
                elif result == "breakeven":
                    symbol_perf[sym]["breakevens"] += 1
                if isinstance(rr, (int, float)):
                    symbol_perf[sym]["rrs"].append(float(rr))

    # Calculate overall metrics
    total_closed_with_result = wins + losses + breakevens
    overall_win_rate = round((wins / total_closed_with_result * 100), 1) if total_closed_with_result > 0 else 0.0
    avg_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else None

    # Post-process template and symbol performance
    def _finalize_perf(d: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        for key, p in d.items():
            closed = p["closed"]
            w = p["wins"]
            wr = round((w / closed * 100), 1) if closed > 0 else 0.0
            rrs = p["rrs"]
            avg = round(sum(rrs) / len(rrs), 2) if rrs else None
            p["win_rate"] = wr
            p["avg_rr"] = avg
            p.pop("rrs", None)  # clean up raw list
        return d

    template_perf = _finalize_perf(template_perf)
    symbol_perf = _finalize_perf(symbol_perf)

    return {
        "total_notes": total,
        "by_status": by_status,
        "by_symbol": by_symbol,
        "by_template": by_template,
        "paper_notes": paper_notes,
        "closed_notes": closed_notes,
        "performance": {
            "wins": wins,
            "losses": losses,
            "breakevens": breakevens,
            "win_rate": overall_win_rate,
            "avg_rr": avg_rr,
            "by_template": template_perf,
            "by_symbol": symbol_perf,
        },
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