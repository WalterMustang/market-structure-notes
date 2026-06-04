# AGENTS.md — Market Structure Notes

This file tells AI agents (Claude, Grok, Cursor, Starchild, etc.) how to work effectively on this project.

## Core Philosophy

This is a **practical daily driver** for a serious trader who does systematic market structure analysis (Wyckoff, SMC/ICT, Price Action, Volume Profile, etc.).

- Real numbers and real usage beat beautiful abstractions.
- Paper trading evidence comes before any live capital or fancy features.
- The .md files are sacred — they must remain human-readable and portable forever.
- Keep the tool small, auditable, and boring in the best way.
- "Smallest useful foundation first" is the rule. No jumping to full live engines, alerts, or overbuilt UIs.

## Architecture (Important)

- **Notes live as plain `.md` files** in `notes/`.
- All structured data (status, P&L, tags, timestamps) lives in `notes/.msn.json`.
- The store (`msn/store.py`) is the single source of truth for metadata.
- CLI and web viewer both read from the store + the .md files.
- Never delete or rewrite user .md files during migrations or refactors.
- Auto-migration must be safe and idempotent.

Current data model (see `msn/store.py` for exact implementation):

```json
{
  "id": "2026-05-29-BTC-4H",
  "status": "paper",           // idea | paper | closed
  "symbol": "BTC",
  "timeframe": "4H",
  "template": "wyckoff",
  "pnl": {
    "direction": "long",       // long | short | null
    "entry": 105000,
    "stop": 103000,            // planned invalidation
    "target": 110000,          // planned target (optional)
    "exit": 108500,
    "rr": 2.5,                 // planned R:R (auto-derived from entry/stop/target)
    "realized_r": 1.75,        // realized R of the outcome (auto-derived; manual wins)
    "result": "win"            // win | loss | breakeven | null
  },
  "tags": ["liquidity"],
  "created_at": "...",
  "updated_at": "...",
  "closed_at": "..."           // stamped when status first becomes "closed"
}
```

`realized_r` is the honest performance metric (expectancy = mean of realized_r over
closed trades). `rr`/`realized_r` are derived from the price fields when present, but
any manually supplied value is never overwritten. Old records are backfilled with
None defaults idempotently by `_ensure_schema()`.

## Development Workflow

1. Make changes in small, testable slices.
2. After any change to `store.py` or CLI commands, run:
   ```bash
   python -m msn stats
   python -m msn list
   python -m msn search "something"
   ```
3. Test the web viewer:
   ```bash
   msn serve
   ```
4. When adding new CLI commands, update both the parser and the help text.
5. When touching the web viewer (inside `create_app()` in `cli.py`), keep the Tailwind + marked.js style consistent.

## Code Review Preferences (Owner: Djani)

- **Audit-first, minimal changes**. Preserve original intent.
- If a refactor is proposed, show the diff and explain the concrete benefit.
- Prefer boring, readable Python over clever abstractions.
- Add comments only where the "why" is non-obvious.
- New features must have a clear paper-trading or review workflow benefit.

## What the Owner Values

- Practical trader output over impressive architecture.
- Clean separation between raw notes (human) and metadata (machine).
- Strong defaults + easy escape hatches.
- Honest docs that reflect reality (see CHANGELOG.md and ROADMAP.md).
- Evidence from actual use before expanding scope.

## Adding New Things

- **New template**: Just drop a `.md` file in `templates/`. No code change needed.
- **New metadata field**: Add it to `_default_meta()` in `store.py`, handle it in `set_note_meta()`, and surface it in CLI/web where useful.
- **New CLI command**: Add to the argparse section in `main()` and implement the handler.
- **New analytics**: Extend `get_stats()` in `store.py` — this is the preferred place for review intelligence.

## Non-Goals (Do Not Suggest These)

- Live order execution or broker integration
- Cloud sync or multi-device "seamless" experience
- AI writing or summarizing the notes
- Heavy web frameworks or databases
- Turning this into a full trading platform

## Current State (as of 2026-06-04)

- Version: 0.3.0
- v0.1 + v0.2 complete (store + CLI + web + P&L + status + search + analytics + export)
- v0.3 complete: completed trade data model (direction/stop/target/realized R +
  `closed_at`), expectancy-first analytics, store backup-on-corrupt + `msn import`
  recovery, first automated test suite (`tests/`, run with `python -m unittest discover -s tests`)
- Next priority: none scheduled. v0.4 (sharing/redaction) is optional/much later —
  don't start speculatively.

## Questions?

When in doubt, make the smallest change that gives the user more visibility into their own closed trades and patterns.

Keep it useful. Keep it small. Keep the .md files clean.