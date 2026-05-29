# Changelog — Market Structure Notes

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-05-29

### Added
- Complete v0.1 roadmap implementation
- Local JSON metadata store (`notes/.msn.json`) with auto-migration for existing `.md` notes
- Structured fields per note: `status` (idea/paper/closed), `pnl` (entry/exit/rr/result), `tags`
- Rich CLI commands:
  - `msn list --status paper --symbol BTC`
  - `msn stats` (win rate, counts by status/symbol/template)
  - `msn status <id> <new_status>`
  - `msn pnl <id> --entry X --exit Y --rr Z --result win`
  - `msn tag <id> <tag>`
  - `msn edit <id>` (opens in $EDITOR with fallback)
- Web viewer fully powered by metadata store:
  - Cards now show status badges, P&L summary, tags
  - Quick status change buttons directly on the list
  - Full P&L editing form on every note's edit page
  - Status filter pills + improved symbol pills
- Better template detection during migration (reads first heading)
- `examples/` folder with realistic starter notes
- `CONTRIBUTING.md` and updated `ROADMAP.md`
- `CHANGELOG.md`

### Changed
- `msn list` now shows status icons, P&L result, and tags by default
- `create_note` automatically registers metadata with correct template
- Version bumped to 0.2.0 (v0.1 feature complete)
- README completely refreshed with new command examples and v0.1 status

### Fixed
- Template field now correctly populated for existing notes

---

## [1.0.0] - 2026-05-29 (Initial personal release)

- Initial CLI + basic web viewer
- Template system (Wyckoff, SMC, etc.)
- Core commands: new, list, search, export, serve

---

## [Unreleased]

### Planned for v0.2+
- Better analytics (win rate by template, avg R:R per symbol)
- Template versioning
- Export to Obsidian/Notion with clean formatting
- Optional GitHub Actions for basic tests on push
- More example notes with real trade reviews

---

**Note**: This tool is for personal note-taking and paper trading analysis only. No live execution.