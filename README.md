# Market Structure Notes

**Structured technical analysis note-taking — CLI + optional web viewer.**

A clean, local-first tool for writing consistent market structure notes using reusable templates (Wyckoff, SMC, Price Action, Volume Profile, Macro, and more). Zero trading logic, zero data collection — just a solid foundation you can extend.

**Public repo:** https://github.com/WalterMustang/market-structure-notes

---

## Why this exists

Most traders write notes in random Markdown files or Notion. Over time it becomes messy and inconsistent. This tool gives you a simple, repeatable structure so every note follows the same logic — making review and pattern recognition much easier.

- 8 ready-to-use templates
- Works completely offline
- Installs in one command
- Optional browser viewer for fast browsing
- Easy to add your own templates

---

## Quick start

```bash
pip install -e .
msn --help
msn templates
msn new --template wyckoff --symbol BTC --timeframe 4H

# v0.1 rich commands
msn list --status paper --symbol BTC
msn stats
msn status 2026-05-29-BTC-4H paper
msn pnl 2026-05-29-BTC-4H --entry 105000 --exit 108500 --rr 2.1 --result win
msn tag 2026-05-29-BTC-4H liquidity
msn edit 2026-05-29-BTC-4H     # opens in $EDITOR

msn serve
```

Then open http://localhost:8765 — the web viewer now shows status, P&L, tags, and lets you change status or log P&L directly from the browser.

---

## Features (v0.1 complete)

- **Templates**: Wyckoff, SMC, Price Action, Minimal, Volume Profile, Macro, Session, and more
- **Rich metadata**: Every note has status (idea/paper/closed), P&L fields, and tags
- **CLI**: `new`, `list` (filter by status/symbol), `stats`, `status`, `pnl`, `tag`, `edit`, `search`, `serve`
- **Web viewer**: Rich cards with status badges, P&L summary, tags + quick status/P&L editing from browser
- **Extensible**: Drop any `.md` file in `templates/` — the CLI discovers it automatically
- **Export**: JSON + zip bundles for Obsidian, Notion, or backup
- **Private & local**: Everything stays on your machine, zero cloud

---

## Installation

```bash
git clone https://github.com/WalterMustang/market-structure-notes.git
cd market-structure-notes
pip install -e .
```

Optional web dependencies:

```bash
pip install 'market-structure-notes[web]'
```

---

## Contributing

We welcome contributions — especially new templates, UI improvements, and bug fixes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started.

Good first issues are labeled `good first issue`.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned work.

v0.1 is complete (data layer, CLI, web upgrades, P&L tracking). See ROADMAP.md for v0.2+.
- Better CLI commands
- Cleaner web viewer

---

## License

MIT — free to use, modify, and distribute.

---

## Status

v1.0.0 — Daily driver ready. Public and open for contributions.

If this helps your workflow, star the repo and share it with others who write structured notes.