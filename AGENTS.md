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
    "entry": 105000,
    "exit": 108500,
    "rr": 2.1,
    "result": "win"            // win | loss | breakeven | null
  },
  "tags": ["liquidity"],
  "created_at": "...",
  "updated_at": "..."
}
```

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

## Current State (as of 2026-05-29)

- Version: 0.2.0
- v0.1 complete (store + CLI + web + P&L + status)
- v0.2 in progress: richer search + real performance analytics (by template & symbol) now working
- Next priority: structured export (Obsidian/Notion friendly with frontmatter)

## Questions?

When in doubt, make the smallest change that gives the user more visibility into their own closed trades and patterns.

Keep it useful. Keep it small. Keep the .md files clean.