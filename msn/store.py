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


def _default_pnl() -> Dict[str, Any]:
    return {
        "direction": None,   # long / short
        "entry": None,
        "stop": None,        # planned invalidation
        "target": None,      # planned target (optional)
        "exit": None,
        "rr": None,          # planned R:R (auto-derivable from entry/stop/target)
        "realized_r": None,  # realized R multiple of the outcome
        "result": None,      # win / loss / breakeven
    }


def _default_meta(note_id: str, symbol: str = "", timeframe: str = "", template: str = "") -> Dict[str, Any]:
    return {
        "id": note_id,
        "status": "idea",
        "symbol": symbol.upper() if symbol else "",
        "timeframe": timeframe.upper() if timeframe else "",
        "template": template,
        "template_hash": "",   # v0.2 simple template versioning
        "pnl": _default_pnl(),
        "tags": [],
        "created_at": _now(),
        "updated_at": _now(),
        "closed_at": None,     # set when the trade is actually closed
    }


def _ensure_schema(meta: Dict[str, Any]) -> bool:
    """Idempotently backfill any missing keys (top-level + pnl) with None defaults.

    Never overwrites existing values, so old records keep their data. Returns True
    if anything was added (so callers can decide whether to persist).
    """
    changed = False
    defaults = _default_meta(meta.get("id", ""))
    for key, value in defaults.items():
        if key == "pnl":
            continue
        if key not in meta:
            meta[key] = value
            changed = True

    pnl = meta.setdefault("pnl", {})
    for key, value in _default_pnl().items():
        if key not in pnl:
            pnl[key] = value
            changed = True

    return changed


def _derive_r(pnl: Dict[str, Any]) -> None:
    """Fill planned rr and realized_r from entry/stop/exit/target when derivable.

    Manual values always win — we only fill fields that are currently None.
    """
    direction = pnl.get("direction")
    entry = pnl.get("entry")
    stop = pnl.get("stop")
    exit_ = pnl.get("exit")
    target = pnl.get("target")

    def _num(x):
        return x if isinstance(x, (int, float)) else None

    entry, stop, exit_, target = _num(entry), _num(stop), _num(exit_), _num(target)
    if entry is None or stop is None:
        return

    risk = abs(entry - stop)
    if risk == 0:
        return

    sign = 1 if direction == "long" else (-1 if direction == "short" else None)

    if pnl.get("realized_r") is None and exit_ is not None and sign is not None:
        pnl["realized_r"] = round(sign * (exit_ - entry) / risk, 2)

    if pnl.get("rr") is None and target is not None:
        pnl["rr"] = round(abs(target - entry) / risk, 2)


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
        # Corrupt file — never silently discard. Back it up with a timestamp and
        # warn so the user can recover (or rebuild via `msn import`).
        backup = STORE_FILE.with_name(
            STORE_FILE.name + ".corrupt-" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        )
        try:
            STORE_FILE.rename(backup)
            print(
                f"WARNING: {STORE_FILE.name} was unreadable. Backed up to {backup.name}. "
                f"Starting a fresh store (rebuild with `msn import --from <dir>`)."
            )
        except Exception:
            print(f"WARNING: {STORE_FILE.name} was unreadable and could not be backed up.")
        return {"version": 1, "notes": {}}


def save_store(data: Dict[str, Any]) -> None:
    ensure_notes_dir()
    STORE_FILE.write_text(json.dumps(data, indent=2))


def _migrate_existing_notes(store: Dict[str, Any]) -> int:
    """Auto-create minimal metadata for any .md files that don't have records yet,
    and backfill the schema on existing records (idempotent)."""
    migrated = 0

    # Backfill schema on existing records so old notes gain new fields safely.
    schema_changed = False
    for meta in store["notes"].values():
        if _ensure_schema(meta):
            schema_changed = True

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

    if migrated > 0 or schema_changed:
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
    _ensure_schema(meta)
    for key, value in updates.items():
        if key == "pnl" and isinstance(value, dict):
            meta["pnl"].update(value)
        else:
            # Allow new keys (template_hash, future fields, etc.) without schema changes every time
            meta[key] = value

    _derive_r(meta["pnl"])
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
    rr_values: List[float] = []           # planned R:R
    realized_values: List[float] = []     # realized R (the honest metric)
    win_r_values: List[float] = []
    loss_r_values: List[float] = []

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
            realized = pnl.get("realized_r")

            if result == "win":
                wins += 1
            elif result == "loss":
                losses += 1
            elif result == "breakeven":
                breakevens += 1

            if isinstance(rr, (int, float)):
                rr_values.append(float(rr))
            if isinstance(realized, (int, float)):
                realized_values.append(float(realized))
                if result == "win":
                    win_r_values.append(float(realized))
                elif result == "loss":
                    loss_r_values.append(float(realized))

            def _accum(d: Dict[str, Dict[str, Any]], k: str):
                if k not in d:
                    d[k] = {"closed": 0, "wins": 0, "losses": 0, "breakevens": 0, "rrs": [], "realized": []}
                p = d[k]
                p["closed"] += 1
                if result == "win":
                    p["wins"] += 1
                elif result == "loss":
                    p["losses"] += 1
                elif result == "breakeven":
                    p["breakevens"] += 1
                if isinstance(rr, (int, float)):
                    p["rrs"].append(float(rr))
                if isinstance(realized, (int, float)):
                    p["realized"].append(float(realized))

            _accum(template_perf, tpl)
            if sym:
                _accum(symbol_perf, sym)

    def _mean(xs: List[float]) -> Optional[float]:
        return round(sum(xs) / len(xs), 2) if xs else None

    # Calculate overall metrics
    total_closed_with_result = wins + losses + breakevens
    overall_win_rate = round((wins / total_closed_with_result * 100), 1) if total_closed_with_result > 0 else 0.0
    avg_rr = _mean(rr_values)              # average *planned* R:R (kept for reference)
    expectancy = _mean(realized_values)   # average *realized* R per trade — the edge
    avg_win_r = _mean(win_r_values)
    avg_loss_r = _mean(loss_r_values)

    # Post-process template and symbol performance
    def _finalize_perf(d: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        for key, p in d.items():
            closed = p["closed"]
            w = p["wins"]
            p["win_rate"] = round((w / closed * 100), 1) if closed > 0 else 0.0
            p["avg_rr"] = _mean(p["rrs"])
            p["expectancy"] = _mean(p["realized"])
            p["realized_count"] = len(p["realized"])
            p.pop("rrs", None)       # clean up raw lists
            p.pop("realized", None)
        return d

    template_perf = _finalize_perf(template_perf)
    symbol_perf = _finalize_perf(symbol_perf)

    # === v0.2 advanced review analytics ===
    # Collect closed trades with result in chronological order for streaks + best setups
    closed_trades = []
    for n in notes:
        if n.get("status") == "closed":
            pnl = n.get("pnl", {}) or {}
            result = pnl.get("result")
            if result in ("win", "loss", "breakeven"):
                closed_trades.append({
                    "id": n.get("id"),
                    # Order by when the trade actually closed; fall back to last edit.
                    "closed_at": n.get("closed_at") or n.get("updated_at", ""),
                    "symbol": n.get("symbol", ""),
                    "template": n.get("template", "") or "unknown",
                    "result": result,
                    "rr": pnl.get("rr"),
                })

    # Sort chronologically (oldest first) for streak calculation
    closed_trades.sort(key=lambda x: x.get("closed_at", ""))

    # Compute streaks
    longest_win = 0
    longest_loss = 0
    current_streak = 0
    current_type = None

    for t in closed_trades:
        if t["result"] == "win":
            if current_type == "win":
                current_streak += 1
            else:
                current_streak = 1
                current_type = "win"
            longest_win = max(longest_win, current_streak)
        elif t["result"] == "loss":
            if current_type == "loss":
                current_streak += 1
            else:
                current_streak = 1
                current_type = "loss"
            longest_loss = max(longest_loss, current_streak)
        else:  # breakeven breaks streaks
            current_streak = 0
            current_type = None

    # Current streak is the last run (positive for win, negative for loss)
    current_streak_value = current_streak if current_type == "win" else (-current_streak if current_type == "loss" else 0)

    # Best performing templates, ranked by expectancy (avg realized R per trade).
    # Require at least 2 trades with a realized R so the ranking means something.
    best_templates = []
    for tpl, p in template_perf.items():
        if p.get("realized_count", 0) >= 2 and p.get("expectancy") is not None:
            best_templates.append({
                "template": tpl,
                "closed": p["closed"],
                "trades_scored": p["realized_count"],
                "win_rate": p["win_rate"],
                "avg_rr": p["avg_rr"],
                "expectancy": p["expectancy"],
            })
    best_templates.sort(key=lambda x: -x["expectancy"])

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
            "expectancy": expectancy,
            "avg_win_r": avg_win_r,
            "avg_loss_r": avg_loss_r,
            "realized_count": len(realized_values),
            "by_template": template_perf,
            "by_symbol": symbol_perf,
        },
        "review": {
            "streaks": {
                "longest_win": longest_win,
                "longest_loss": longest_loss,
                "current": current_streak_value,
            },
            "best_templates": best_templates[:5],  # top 5
        },
    }


def update_pnl(
    note_id: str,
    entry: Any = None,
    exit: Any = None,
    rr: Any = None,
    result: Optional[str] = None,
    direction: Optional[str] = None,
    stop: Any = None,
    target: Any = None,
    realized_r: Any = None,
) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    if direction is not None:
        updates["direction"] = direction
    if entry is not None:
        updates["entry"] = entry
    if stop is not None:
        updates["stop"] = stop
    if target is not None:
        updates["target"] = target
    if exit is not None:
        updates["exit"] = exit
    if rr is not None:
        updates["rr"] = rr
    if realized_r is not None:
        updates["realized_r"] = realized_r
    if result is not None:
        updates["result"] = result

    return set_note_meta(note_id, pnl=updates)


def set_status(note_id: str, status: str) -> Dict[str, Any]:
    valid = {"idea", "paper", "closed"}
    if status not in valid:
        raise ValueError(f"Invalid status. Must be one of: {valid}")

    updates: Dict[str, Any] = {"status": status}
    # Stamp the actual close time once, so streak ordering reflects when the trade
    # closed rather than when the note was last edited.
    if status == "closed":
        existing = get_note_meta(note_id)
        if not existing or not existing.get("closed_at"):
            updates["closed_at"] = _now()
    return set_note_meta(note_id, **updates)


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