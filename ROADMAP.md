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
- Structured export:
  - `msn export --format structured` → rich JSON (full metadata + markdown content)
  - `msn export --format markdown` → individual .md files with proper YAML frontmatter (ready for Obsidian / Logseq / Notion)
- More review analytics:
  - Streaks (longest win/loss, current streak)
  - Best performing templates (scored by win% × avg RR, min sample size)

### v0.2 complete
- Improved `msn edit` fallback (clear file path + editor suggestions when $EDITOR not set)
- Note linking convention documented: use `[[NOTE-ID]]` in markdown for cross-references (human + future machine readable)
- Template hash surfaced in `--verbose` list and structured exports (ties into the versioning work)

---

## v0.3 — Correctness & durability (Complete)

**Goal**: Make the numbers honest and the metadata recoverable. v0.2 shipped
analytics that were subtly wrong and a metadata layer with no backup story; this
lane fixes both before adding more surface.

### Delivered
- **Trade data model completed**: `pnl` now carries `direction` (long/short),
  `stop`, `target`, and `realized_r`, plus a real `closed_at` on the note. The tool
  *derives* realized R and planned R:R from price/stop instead of trusting a typed-in
  number.
- **Expectancy-first analytics**: `msn stats` now leads with expectancy
  (avg realized R per trade) and avg win/loss R. Best setups are ranked by
  expectancy, not the old `win% × planned_rr` score.
- **Durable + recoverable store**: a corrupt `.msn.json` is backed up
  (`.msn.json.corrupt-<ts>`) and warned about instead of silently wiped. New
  `msn import --from <dir>` rebuilds/merges the store from exported Markdown
  frontmatter (read-only; never writes into `notes/`).
- **First automated tests**: a stdlib `unittest` suite covers schema/migration,
  R derivation, expectancy, streak ordering, and the import round-trip.

### Bugs fixed (were shipped as "features" in v0.2)
- `avg_rr` averaged *planned* R:R across closed trades regardless of outcome — a
  losing 3R plan still counted as +3. It is now clearly labelled "planned" and is
  no longer the headline metric.
- Streaks ordered by note `updated_at`, so editing an old note silently re-ordered
  your win/loss chronology. They now order by `closed_at`.

---

## v0.4 — Sharing & community (optional, much later)

- **Redaction engine** (the reusable, locally-valuable half — build first if anything):
  strip size/account/identifying detail from a note for safe sharing.
- Public read-only note viewer (self-hosted or static).
- Template gallery (community contributions).
- *Questioned / much later:* social "publish to X / AgentX". Leans against the
  local-first, no-cloud-sync spirit; only worth it once the redaction engine exists
  and there's real demand.

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

**Current status**: v0.3 complete (2026-06-04). Correctness & durability: completed
trade data model (direction/stop/target/realized R + `closed_at`), expectancy-first
analytics, store backup-on-corrupt + `msn import` recovery, and the first automated
test suite. Fixed the v0.2 `avg_rr` inflation and streak-ordering bugs.

See git history and CHANGELOG.md for exact changes.