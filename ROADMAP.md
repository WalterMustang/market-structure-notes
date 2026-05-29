# Roadmap — Market Structure Notes

This is the public roadmap. It is intentionally small and focused.

---

## v0.1 — Core daily driver (Complete)

**Goal**: Make the tool genuinely useful for daily note-taking and review.

### Delivered
- Local JSON metadata store (`notes/.msn.json`) with automatic migration for existing `.md` notes
- Structured fields: `status` (idea/paper/closed), `pnl` (entry/exit/rr/result), `tags`
- Rich CLI: `list --status/--symbol`, `stats`, `status`, `pnl`, `tag`, `edit`, improved `search`
- Web viewer fully powered by metadata (status badges, P&L, quick actions, editing forms)
- Packaging, docs, examples, CI basics

**Split**:
- User (with Grok 4.3): Template refinement, schema decisions, real example notes
- Starchild: Engineering, data layer, CLI + web, packaging

---

## v0.2 — Review & pattern tools (In progress)

**Goal**: Turn the journal into something you can actually learn from.

### Delivered (so far)
- `msn search` now searches across metadata + content (status, tags, P&L result, template, etc.)
- `msn stats` with real analytics:
  - Win rate + average R:R overall
  - Breakdown by template and by symbol (closed trades only)
- Better template detection during migration

### Remaining / Next
- Structured export (`msn export structured` or similar)
  - JSON with full metadata
  - Markdown files with YAML frontmatter for Obsidian / Notion / Logseq
- More review analytics (e.g. best performing setups, streaks, time-based filters)
- Template versioning (simple)
- Improved `msn edit` experience and note linking

---

## v0.3 — Sharing & community (optional, later)

- Public read-only note viewer (self-hosted or static)
- One-click publish to X / AgentX (with proper redaction)
- Template gallery (community contributions)

---

## Non-goals

- No live trading execution
- No cloud sync
- No AI-generated analysis
- No personal trading signals in the core repo
- No over-engineering before real usage data exists

---

## How to influence the roadmap

Open an issue with:
- What you actually want to do with the tool day-to-day
- Why current features are not enough

We prioritize based on real daily usage and paper trading evidence, not feature requests.

---

**Current status**: v0.2.0 — v0.1 complete. v0.2 analytics + search delivered. Next focus: structured export + deeper review tools.

See git history and CHANGELOG.md for exact changes.