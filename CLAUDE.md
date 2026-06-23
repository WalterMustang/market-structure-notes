# CLAUDE.md

Quick orientation for Claude Code. **`AGENTS.md` is the source of truth** —
read it for philosophy, architecture, the data model, code-review preferences,
and non-goals. This file covers the high-frequency facts plus the traps that
aren't obvious from a first read.

## What this is

Market Structure Notes (`msn`) — a CLI + optional web tool for writing
structured technical-analysis notes (Wyckoff, SMC/ICT, Price Action, etc.).
Local-first, pure-stdlib core, Python ≥3.10. Current version: 0.3.0 (verify in
`pyproject.toml`; `--version` reads `__version__` in `msn/__init__.py`, so bump both).

## Key paths

- `msn/cli.py` — **the live entrypoint** (`msn = "msn.cli:main"` in
  `pyproject.toml`). Holds the argparse CLI *and* the entire web viewer in
  `create_app()` (inline Tailwind + marked.js).
- `msn/store.py` — metadata store; **single source of truth** for status, P&L,
  tags, timestamps (persisted to `notes/.msn.json`). CLI and web both read it.
- `templates/` — note templates; drop in a new `.md` and it's auto-discovered
  (7 templates today, even though some prose says 8 — trust `ls templates/`).
- `notes/` — user notes as plain `.md` files + the `.msn.json` metadata store.
- `scripts/msn.py` — **legacy v1.0.0 standalone (no store, json-only export).**
  Do **not** edit it for current work, despite `project.yaml` still pointing at
  it as `entry`. If you're touching CLI behavior, it's `msn/cli.py`.

## CLI surface

The 12 subcommands wired up in `main()` in `cli.py` (each also runs via
`python -m msn <cmd>` — see `msn/__main__.py`). Keep `--help` text in sync when
you touch any of them:

- `new --template <t> --symbol <s> --timeframe <tf> [--date]` — create a note
- `list [--filter] [--status idea|paper|closed] [--symbol] [--verbose]`
- `search <query>` — searches metadata + content
- `export --format {json|structured|markdown}` (markdown = YAML frontmatter,
  Obsidian/Notion-ready; pairs with `import`)
- `templates` — list discovered templates
- `stats` — counts + expectancy-first closed-trade analytics
- `status <note_id> <idea|paper|closed>`
- `pnl <note_id> [--direction --entry --stop --target --exit --rr --realized-r --result]`
- `tag <note_id> <tag>`
- `edit <note_id>` — open in `$EDITOR` (prints path + suggestions if unset)
- `import --from <dir>` — rebuild/merge store from exported markdown frontmatter
  (read-only; never writes into `notes/`)
- `serve [--port 8765]` — web viewer (needs the `[web]` extra)

## How to work here

- Smallest useful change first. Audit-first, minimal diffs; preserve original
  intent. Prefer boring, readable Python over clever abstractions.
- A new feature must earn its place via a concrete paper-trading / review
  workflow benefit. No speculative building.
- Respect the non-goals (no live execution/broker, no cloud sync, no AI-written
  notes, no heavy web frameworks or databases) — see AGENTS.md "Non-Goals".
- Comments only where the "why" is non-obvious.

## Roadmap & extension

- v0.1, v0.2, and v0.3 (correctness & durability) are complete. v0.4
  (sharing/redaction) is optional/much later — don't start it speculatively. Check
  `ROADMAP.md` + `CHANGELOG.md` for live status.
- Where to extend (see AGENTS.md "Adding New Things"):
  - **Template** → drop a `.md` in `templates/`. No code change.
  - **Metadata field** → `_default_meta()` + `set_note_meta()` in `store.py`,
    then surface in CLI/web.
  - **Analytics** → extend `get_stats()` in `store.py` (preferred home for
    review intelligence).
  - **CLI command** → add the argparse block in `main()` and its handler in
    `cli.py` (keep `--help` text in sync).

## Validation

A stdlib `unittest` suite lives in `tests/` (as of v0.3): `test_store.py`
(schema/migration, R derivation, corrupt-store recovery), `test_stats.py`
(expectancy + streak ordering), `test_io.py` (export→import round-trip). Run it
plus the smoke gate that CI runs (`.github/workflows/ci.yml`, Python 3.10–3.12):

```bash
python -m unittest discover -s tests             # store/analytics/import tests
msn --version && msn templates && msn stats
python -c "from msn.cli import create_app; create_app()"   # web imports
```

For web-viewer changes also run `msn serve` (default http://localhost:8765) and
click through. Run the gate before claiming a change works.

```bash
pip install -e .            # core (no deps)
pip install -e '.[web]'     # add FastAPI/Uvicorn for `msn serve`
```

## Bugs, debt & maintainability

- **Hard rule:** never delete or rewrite user `.md` files during migrations or
  refactors. Auto-migration (`_migrate_existing_notes` in `store.py`) must stay
  safe and idempotent.
- Keep the web viewer's file routes path-traversal safe — route user-supplied
  filenames through `_safe_note_path()` in `cli.py`; never open raw paths.
- Known legacy debt: `scripts/msn.py` and `project.yaml` still describe the old
  v1.0.0 tool. Leave it unless explicitly asked — don't scope-creep.
- Docs drift (version, template count) across files. Owner values honest docs:
  verify numbers from `pyproject.toml` / `ls templates/` before repeating them,
  and keep `CHANGELOG.md` + `ROADMAP.md` truthful when you ship.
