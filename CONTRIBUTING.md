# Contributing to Market Structure Notes

Thanks for your interest in improving this tool.

The goal is to keep the project simple, local-first, and genuinely useful for traders who want consistent note-taking.

---

## How to contribute

### 1. Templates (easiest way to start)

The fastest contribution is adding or improving a template.

1. Fork the repo
2. Create a new `.md` file in `templates/`
3. Use these placeholders where needed:
   - `{{date}}`
   - `{{symbol}}`
   - `{{timeframe}}`
4. Open a pull request with a short description of what the template helps analyze

Example template names:
- `elliott-wave.md`
- `orderflow.md`
- `breakout.md`

### 2. Code & Features

- CLI improvements
- Web viewer enhancements
- Search / export features
- Documentation

Before starting a larger change, open an issue first so we can discuss scope.

### 3. Bug reports

Open an issue with:
- What you ran
- What happened
- What you expected

---

## Development setup

```bash
git clone https://github.com/WalterMustang/market-structure-notes.git
cd market-structure-notes
pip install -e '.[web]'
```

Run the CLI:

```bash
msn --help
```

Run the web viewer:

```bash
msn serve
```

---

## Code style

- Keep it simple and readable
- Prefer small, focused functions
- No unnecessary dependencies
- CLI commands should feel natural

---

## Pull request checklist

- [ ] Tested locally (`msn new`, `msn list`, `msn serve`)
- [ ] New templates include the three placeholders
- [ ] README or docs updated if behavior changes
- [ ] One focused change per PR

---

## Questions?

Open an issue or start a discussion. We keep things practical.