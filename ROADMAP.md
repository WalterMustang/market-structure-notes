# Roadmap — Market Structure Notes

This is the public roadmap. It is intentionally small and focused.

---

## v0.1 — Core daily driver (Current)

**Goal**: Make the tool genuinely useful for daily note-taking and review.

### Planned work
- Local JSON database for notes (search, filter, stats)
- Better CLI commands (`msn new`, `msn list`, `msn export`, `msn stats`)
- Web viewer improvements (symbol filters, status tracking, keyboard shortcuts)
- P&L logging fields (paper trading only)
- Cleaner README + contribution flow

**Split**:
- User (with Grok 4.3): Template refinement, schema decisions, real example notes
- Starchild: Engineering, data layer, CLI polish, packaging

---

## v0.2 — Review & pattern tools

- Note search across all fields
- Basic analytics (win rate by template, avg R:R, best symbols)
- Export to Obsidian / Notion with proper formatting
- Template versioning

---

## v0.3 — Sharing & community (optional)

- Public read-only note viewer
- One-click publish to X / AgentX
- Template gallery (community contributions)

---

## Non-goals

- No live trading execution
- No cloud sync
- No AI-generated analysis
- No personal trading signals in the core repo

---

## How to influence the roadmap

Open an issue with:
- What you want to do with the tool
- Why current features are not enough

We prioritize based on real daily usage, not feature requests.

---

**Current status**: v1.0.0 released. v0.1 work starting.