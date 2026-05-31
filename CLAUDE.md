# CLAUDE.md

Quick orientation for Claude Code. **`AGENTS.md` is the source of truth** —
read it for philosophy, architecture, the data model, code-review preferences,
and non-goals. This file just covers the high-frequency facts.

## What this is

Market Structure Notes (`msn`) — a CLI + optional web tool for writing
structured technical-analysis notes (Wyckoff, SMC/ICT, Price Action, etc.).
Local-first, pure-stdlib core, Python ≥3.10. Current version: 0.2.1.

## Key paths

- `msn/store.py` — metadata store; **single source of truth** for status, P&L,
  tags, timestamps (persisted to `notes/.msn.json`).
- `msn/cli.py` — argparse CLI plus the web viewer in `create_app()`
  (Tailwind + marked.js).
- `notes/` — user notes as plain `.md` files + the `.msn.json` metadata store.
- `templates/` — note templates; drop in a new `.md` file and it's auto-discovered.

## Common commands

```bash
pip install -e .                 # core (no deps)
pip install -e '.[web]'          # add FastAPI/Uvicorn for `msn serve`

python -m msn list               # list notes
python -m msn stats              # analytics
python -m msn search "term"      # search
msn serve                        # web viewer at http://localhost:8765
```

## Hard rule

Never delete or rewrite user `.md` files during migrations or refactors.
Auto-migration must be safe and idempotent.

## Testing

No automated test suite yet — verify changes manually with the CLI commands
above (and `msn serve` for the web viewer), per the Development Workflow in
`AGENTS.md`.
