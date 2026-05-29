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
msn list
msn serve
```

Then open http://localhost:8765 to browse all your notes in the browser.

---

## Features

- **Templates**: Wyckoff, SMC, Price Action, Minimal, Volume Profile, Macro, Session, and more
- **CLI**: Create, list, search, and export notes from the terminal
- **Web viewer**: Side-by-side editing with live preview and symbol filters
- **Extensible**: Drop any `.md` file in `templates/` — the CLI discovers it automatically
- **Export**: JSON + zip bundles for Obsidian, Notion, or backup
- **Private**: Everything stays on your machine

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

Current focus (v0.1):
- Stronger data layer (search, stats, P&L logging)
- Better CLI commands
- Cleaner web viewer

---

## License

MIT — free to use, modify, and distribute.

---

## Status

v1.0.0 — Daily driver ready. Public and open for contributions.

If this helps your workflow, star the repo and share it with others who write structured notes.