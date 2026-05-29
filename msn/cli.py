#!/usr/bin/env python3
"""
Market Structure Notes (MSN) - CLI + optional web viewer.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "templates"
NOTES_DIR = ROOT / "notes"

# Import the new metadata store (v0.1)
from msn.store import (
    get_stats,
    list_notes_meta,
    set_status,
    update_pnl,
    add_tag,
    set_note_meta,
    get_note_meta,
    load_store,
    _migrate_existing_notes,
)


def ensure_notes_dir():
    NOTES_DIR.mkdir(exist_ok=True)


def list_templates():
    return sorted([p.stem for p in TEMPLATES_DIR.glob("*.md")])


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Template '{name}' not found")
    return path.read_text()


def substitute(template: str, values: dict) -> str:
    def replacer(match):
        key = match.group(1)
        return str(values.get(key, f"{{{{{key}}}}}"))
    return re.sub(r"\{\{(\w+)\}\}", replacer, template)


def create_note(template_name: str, symbol: str, timeframe: str, date_str: str = None):
    ensure_notes_dir()
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    template = load_template(template_name)
    values = {
        "date": date_str,
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper()
    }
    content = substitute(template, values)

    filename = f"{date_str}-{symbol.upper()}-{timeframe.upper()}.md"
    filepath = NOTES_DIR / filename
    filepath.write_text(content)

    # Register in the metadata store (v0.1)
    note_id = filename.replace(".md", "")
    set_note_meta(
        note_id,
        status="idea",
        symbol=symbol.upper(),
        timeframe=timeframe.upper(),
        template=template_name,
    )

    print(f"Created: {filepath.relative_to(ROOT)}  (status=idea)")
    return filepath


def list_notes(filter_str: str = None, status: str = None, symbol: str = None):
    ensure_notes_dir()

    # Use the new metadata store for rich listing (v0.1)
    notes = list_notes_meta(status=status, symbol=symbol)

    # Optional simple text filter on filename
    if filter_str:
        notes = [n for n in notes if filter_str.lower() in n.get("id", "").lower()]

    if not notes:
        print("No notes found.")
        return

    print(f"Found {len(notes)} notes:\n")
    for n in notes:
        status_icon = {
            "idea": "💡",
            "paper": "📝",
            "closed": "✅",
        }.get(n.get("status"), "•")

        pnl = n.get("pnl", {})
        pnl_str = ""
        if pnl.get("result"):
            pnl_str = f" | {pnl['result'].upper()}"
        elif pnl.get("entry"):
            pnl_str = f" | entry:{pnl.get('entry')}"

        tags = n.get("tags", [])
        tags_str = f"  [{', '.join(tags)}]" if tags else ""

        print(f"  {status_icon} {n['id']:<30}  {n.get('status','idea'):<7}  {n.get('symbol',''):<6} {n.get('timeframe',''):<4}{pnl_str}{tags_str}")


def search_notes(query: str):
    """Search across both metadata (status, tags, P&L, symbol, template) and note content. v0.2 upgrade."""
    ensure_notes_dir()
    q = query.lower()

    # Get all notes with metadata
    meta_results = list_notes_meta()

    matches = []
    for m in meta_results:
        nid = m["id"]
        content = ""
        md_path = NOTES_DIR / f"{nid}.md"
        if md_path.exists():
            content = md_path.read_text().lower()

        # Search in metadata fields + content
        haystack = " ".join([
            nid.lower(),
            m.get("symbol", "").lower(),
            m.get("template", "").lower(),
            m.get("status", ""),
            " ".join(m.get("tags", [])),
            str(m.get("pnl", {}).get("result", "")),
            content
        ])

        if q in haystack:
            matches.append(m)

    if not matches:
        print(f"No matches for '{query}'")
        return

    print(f"Found {len(matches)} match(es) for '{query}':\n")
    for m in matches:
        status_icon = {"idea": "💡", "paper": "📝", "closed": "✅"}.get(m.get("status"), "•")
        pnl = m.get("pnl", {})
        extra = ""
        if pnl.get("result"):
            extra = f" | {pnl['result'].upper()}"
        tags = f" [{', '.join(m.get('tags', []))}]" if m.get("tags") else ""
        print(f"  {status_icon} {m['id']}  {m.get('status')}{extra}{tags}")


def edit_note_cli(note_id: str):
    """Open a note in $EDITOR (or fallback to simple input)."""
    ensure_notes_dir()
    # Find the file (note_id can be full name or stem)
    candidates = list(NOTES_DIR.glob(f"{note_id}*.md"))
    if not candidates:
        # Try exact
        path = NOTES_DIR / (note_id if note_id.endswith(".md") else f"{note_id}.md")
        if not path.exists():
            print(f"Note not found: {note_id}")
            return
    else:
        path = candidates[0]

    import os
    import subprocess

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    try:
        subprocess.call([editor, str(path)])
    except FileNotFoundError:
        print(f"Editor '{editor}' not found. Falling back to simple edit.")
        print(f"Current content of {path.name}:")
        print(path.read_text())
        print("\n--- Paste new full content (end with EOF) ---")
        new_content = []
        try:
            while True:
                line = input()
                new_content.append(line)
        except EOFError:
            pass
        path.write_text("\n".join(new_content))
        print("Saved.")

    # Touch the metadata updated_at
    set_note_meta(note_id.replace(".md", ""), updated_at=None)  # will set current time inside set_note_meta
    print(f"Opened/edited: {path.name}")


def export_notes(fmt: str = "json"):
    ensure_notes_dir()
    md_files = sorted(NOTES_DIR.glob("*.md"), reverse=True)
    if not md_files:
        print("No notes to export.")
        return

    if fmt == "json":
        # Legacy simple export (raw content only)
        data = [{"filename": n.name, "content": n.read_text()} for n in md_files]
        out = ROOT / "export.json"
        out.write_text(json.dumps(data, indent=2))
        print(f"Exported {len(md_files)} notes to export.json (legacy format)")

    elif fmt == "structured":
        # v0.2 structured export: full metadata + markdown (ideal for Obsidian, Notion, analysis)
        store = load_store()
        _migrate_existing_notes(store)

        export_data = []
        for md_file in md_files:
            note_id = md_file.stem
            meta = store["notes"].get(note_id, {})
            export_data.append({
                "id": note_id,
                "meta": meta,
                "markdown": md_file.read_text(),
            })

        out_path = ROOT / "export-structured.json"
        from datetime import datetime
        out_path.write_text(json.dumps({
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "version": "0.2",
            "count": len(export_data),
            "notes": export_data
        }, indent=2))

        print(f"Exported {len(export_data)} notes with full metadata to export-structured.json")
        print("This file contains status, P&L, tags + full markdown — perfect for Obsidian/Notion import or custom analysis.")

    elif fmt == "markdown":
        # v0.2: Obsidian / Notion / Logseq friendly export with real YAML frontmatter
        store = load_store()
        _migrate_existing_notes(store)

        export_dir = ROOT / "export" / "markdown"
        export_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for md_file in md_files:
            note_id = md_file.stem
            meta = store["notes"].get(note_id, {})
            original_content = md_file.read_text()

            frontmatter = _build_yaml_frontmatter(meta)
            full_file = frontmatter + "\n" + original_content

            out_file = export_dir / f"{note_id}.md"
            out_file.write_text(full_file)
            count += 1

        print(f"Exported {count} notes as Markdown + YAML frontmatter → export/markdown/")
        print("Drop the whole folder straight into Obsidian, Logseq, or Notion. Frontmatter is real YAML.")


def _build_yaml_frontmatter(meta: dict) -> str:
    """Generate clean YAML frontmatter for Obsidian-style notes. Zero external deps."""
    lines = ["---"]

    # Core identity
    lines.append(f"id: {meta.get('id', '')}")
    lines.append(f"status: {meta.get('status', 'idea')}")
    if meta.get("symbol"):
        lines.append(f"symbol: {meta.get('symbol')}")
    if meta.get("timeframe"):
        lines.append(f"timeframe: {meta.get('timeframe')}")
    if meta.get("template"):
        lines.append(f"template: {meta.get('template')}")

    # P&L block
    pnl = meta.get("pnl", {}) or {}
    if any(pnl.get(k) is not None for k in ("entry", "exit", "rr", "result")):
        lines.append("pnl:")
        if pnl.get("entry") is not None:
            lines.append(f"  entry: {pnl['entry']}")
        if pnl.get("exit") is not None:
            lines.append(f"  exit: {pnl['exit']}")
        if pnl.get("rr") is not None:
            lines.append(f"  rr: {pnl['rr']}")
        if pnl.get("result"):
            lines.append(f"  result: {pnl['result']}")

    # Tags
    tags = meta.get("tags", [])
    if tags:
        lines.append("tags:")
        for t in tags:
            lines.append(f"  - {t}")

    # Timestamps
    if meta.get("created_at"):
        lines.append(f"created_at: {meta['created_at']}")
    if meta.get("updated_at"):
        lines.append(f"updated_at: {meta['updated_at']}")

    lines.append("---")
    return "\n".join(lines)


def create_app():
    """Create the FastAPI web viewer app (reusable for CLI and previews)."""
    try:
        from fastapi import FastAPI, Form
        from fastapi.responses import HTMLResponse, RedirectResponse
        from jinja2 import Template
    except ImportError:
        raise RuntimeError(
            "Web dependencies missing.\n"
            "Install with: pip install 'market-structure-notes[web]'\n"
            "This pulls in FastAPI, Uvicorn, Jinja2, and python-multipart (required for form handling)."
        )

    app = FastAPI(title="Market Structure Notes")

    BASE_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>MSN • Market Structure Notes</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }
            .note-card { transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
            .note-card:hover { transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.05); }
            pre { font-size: 13px; line-height: 1.5; }
            .modal { animation: fadeInScale 0.2s ease-out; }
            @keyframes fadeInScale { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        </style>
    </head>
    <body class="bg-zinc-950 text-zinc-200">
        <div class="max-w-6xl mx-auto px-6 py-8">
            <div class="flex items-center justify-between mb-8">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 bg-white rounded-xl flex items-center justify-center">
                        <span class="text-zinc-950 font-bold text-xl">M</span>
                    </div>
                    <div>
                        <div class="font-semibold text-2xl tracking-tight">Market Structure Notes</div>
                        <div class="text-xs text-zinc-500 -mt-1">v1.0.0</div>
                    </div>
                </div>
                <div class="flex items-center gap-4 text-sm">
                    <a href="/" class="px-4 py-2 rounded-xl hover:bg-zinc-900 transition-colors">Notes</a>
                    <a href="/templates" class="px-4 py-2 rounded-xl hover:bg-zinc-900 transition-colors">Templates</a>
                    <button onclick="showCreateModal()" 
                            class="px-5 py-2 bg-white text-zinc-950 rounded-2xl text-sm font-medium hover:bg-zinc-200 transition-colors">+ New Note</button>
                    <a href="https://github.com/Starchild-ai-agent/community-projects" target="_blank" 
                       class="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition-colors">GitHub</a>
                </div>
            </div>
            {{content}}
        </div>

        <!-- Create Modal -->
        <div id="createModal" class="hidden fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div class="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 w-full max-w-lg modal">
                <div class="flex justify-between items-center mb-6">
                    <div class="font-semibold text-xl">Create New Note</div>
                    <button onclick="hideCreateModal()" class="text-zinc-500 hover:text-white">✕</button>
                </div>
                <form method="post" action="/create">
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div>
                            <label class="text-xs text-zinc-500 block mb-1">Template</label>
                            <select name="template" class="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-4 py-3 text-sm">
                                {% for t in templates %}<option value="{{t}}">{{t}}</option>{% endfor %}
                            </select>
                        </div>
                        <div>
                            <label class="text-xs text-zinc-500 block mb-1">Symbol</label>
                            <input type="text" name="symbol" value="BTC" class="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-4 py-3 text-sm font-mono">
                        </div>
                    </div>
                    <div class="mb-6">
                        <label class="text-xs text-zinc-500 block mb-1">Timeframe</label>
                        <input type="text" name="timeframe" value="4H" class="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-4 py-3 text-sm font-mono">
                    </div>
                    <div class="flex gap-3">
                        <button type="button" onclick="hideCreateModal()" 
                                class="flex-1 py-3 rounded-2xl bg-zinc-800 hover:bg-zinc-700 transition-colors text-sm">Cancel</button>
                        <button type="submit" 
                                class="flex-1 py-3 rounded-2xl bg-white text-zinc-950 font-medium text-sm">Create Note</button>
                    </div>
                </form>
            </div>
        </div>

        <script>
            function showCreateModal() {
                document.getElementById('createModal').classList.remove('hidden');
                document.getElementById('createModal').classList.add('flex');
            }
            function hideCreateModal() {
                document.getElementById('createModal').classList.add('hidden');
                document.getElementById('createModal').classList.remove('flex');
            }
            // Close modal on escape
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') hideCreateModal();
            });
        </script>
    </body>
    </html>
    """

    @app.get("/", response_class=HTMLResponse)
    def index(q: str = "", symbol: str = "", status: str = ""):
        ensure_notes_dir()

        # === v0.1: Use the metadata store for rich data ===
        meta_notes = list_notes_meta(status=status if status else None, symbol=symbol if symbol else None)

        # Apply text search on top of metadata results (search in id + tags + we will check content if needed)
        if q:
            filtered = []
            for m in meta_notes:
                note_path = NOTES_DIR / f"{m['id']}.md"
                content = note_path.read_text().lower() if note_path.exists() else ""
                if (q.lower() in m['id'].lower() or
                    q.lower() in " ".join(m.get('tags', [])) or
                    q.lower() in content):
                    filtered.append(m)
            meta_notes = filtered

        # Build symbol set for pills (from store for speed)
        all_symbols = set(m['symbol'] for m in list_notes_meta() if m.get('symbol'))

        # Current active filter display
        filter_pill = ""
        active_filters = []
        if symbol:
            active_filters.append(f"symbol:{symbol}")
        if status:
            active_filters.append(f"status:{status}")
        if active_filters:
            filter_pill = f'<a href="/" class="inline-flex items-center gap-1 px-3 py-1 bg-white text-zinc-950 text-xs rounded-full font-medium">Filtering: {" + ".join(active_filters)} <span class="text-zinc-500">×</span></a>'

        # Symbol pills (clickable)
        symbol_pills = ""
        if all_symbols:
            pills = []
            for sym in sorted(all_symbols):
                active = "bg-white text-zinc-950" if sym == symbol else "bg-zinc-800 hover:bg-zinc-700"
                pills.append(f'<a href="/?symbol={sym}{"&status="+status if status else ""}" class="px-3 py-1 text-xs rounded-full {active} transition-colors">{sym}</a>')
            symbol_pills = "".join(pills)

        # Status filter pills (new in v0.1)
        status_pills = ""
        status_options = ["idea", "paper", "closed"]
        status_labels = {"idea": "💡 Idea", "paper": "📝 Paper", "closed": "✅ Closed"}
        st_pills = []
        for st in status_options:
            active = "bg-white text-zinc-950" if st == status else "bg-zinc-800 hover:bg-zinc-700"
            href = f"/?status={st}"
            if symbol: href += f"&symbol={symbol}"
            st_pills.append(f'<a href="{href}" class="px-3 py-1 text-xs rounded-full {active} transition-colors">{status_labels[st]}</a>')
        status_pills = "".join(st_pills)
        
        # Use real stats from store (v0.1)
        store_stats = get_stats()

        stats_html = f"""
        <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="bg-zinc-900 rounded-3xl p-6">
                <div class="text-sm text-zinc-500">Total Notes</div>
                <div class="text-4xl font-semibold mt-2">{store_stats['total_notes']}</div>
            </div>
            <div class="bg-zinc-900 rounded-3xl p-6">
                <div class="text-sm text-zinc-500 mb-2">Symbols Tracked</div>
                <div class="flex flex-wrap gap-1.5">{symbol_pills or '<span class="text-xs text-zinc-500">No symbols yet</span>'}</div>
            </div>
            <div class="bg-zinc-900 rounded-3xl p-6">
                <div class="text-sm text-zinc-500 mb-1">Status</div>
                <div class="flex flex-wrap gap-1.5">{status_pills}</div>
            </div>
            <div class="bg-zinc-900 rounded-3xl p-6">
                <div class="text-sm text-zinc-500">Win Rate (closed)</div>
                <div class="text-4xl font-semibold mt-1">{store_stats['win_rate']}% <span class="text-sm text-zinc-500">({store_stats['wins']}W / {store_stats['losses']}L)</span></div>
            </div>
        </div>
        {f'<div class="mb-4">{filter_pill}</div>' if filter_pill else ''}
        """

        search_html = f"""
        <div class="mb-6 flex gap-3">
            <form method="get" class="flex-1 flex gap-2">
                <input type="text" name="q" value="{q}" placeholder="Search notes..." 
                       class="flex-1 bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-3 text-sm focus:outline-none focus:border-zinc-700">
                {f'<input type="hidden" name="symbol" value="{symbol}">' if symbol else ''}
                <button type="submit" class="px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-medium">Search</button>
            </form>
            <button onclick="showCreateModal()" 
                    class="px-6 py-3 bg-white text-zinc-950 rounded-2xl text-sm font-medium whitespace-nowrap">+ Quick Create</button>
        </div>
        """

        # Export bar (v1.0)
        export_html = """
        <div class="flex items-center gap-3 mb-6 text-sm">
            <div class="text-zinc-500">Export:</div>
            <a href="/export/json" class="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-xs font-medium">JSON</a>
            <a href="/export/all" class="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-xs font-medium">All Notes (.zip)</a>
        </div>
        """

        notes_html = ""
        if meta_notes:
            for m in meta_notes:
                nid = m['id']
                status = m.get('status', 'idea')
                status_badge = {
                    'idea': '<span class="px-2 py-0.5 text-[10px] rounded-full bg-amber-900/60 text-amber-300">IDEA</span>',
                    'paper': '<span class="px-2 py-0.5 text-[10px] rounded-full bg-blue-900/60 text-blue-300">PAPER</span>',
                    'closed': '<span class="px-2 py-0.5 text-[10px] rounded-full bg-emerald-900/60 text-emerald-300">CLOSED</span>',
                }.get(status, '')

                pnl = m.get('pnl', {})
                pnl_html = ""
                if pnl.get('result'):
                    color = "text-emerald-400" if pnl['result'] == 'win' else ("text-red-400" if pnl['result'] == 'loss' else "text-zinc-400")
                    pnl_html = f'<span class="{color} text-xs font-medium">{pnl["result"].upper()}</span> R:R {pnl.get("rr", "?")}'
                elif pnl.get('entry'):
                    pnl_html = f'<span class="text-xs text-zinc-400">entry {pnl.get("entry")}</span>'

                tags_html = ""
                if m.get('tags'):
                    tags_html = " ".join([f'<span class="text-[10px] px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">#{t}</span>' for t in m['tags']])

                notes_html += f"""
                <div class="note-card bg-zinc-900 border border-zinc-800 rounded-3xl p-5 mb-3 hover:border-zinc-700">
                    <div class="flex items-start justify-between mb-2">
                        <a href="/edit/{nid}.md" class="font-mono text-sm text-white hover:underline">{nid}</a>
                        <div class="flex items-center gap-2">
                            {status_badge}
                            <a href="/edit/{nid}.md" class="text-[10px] px-2 py-0.5 bg-zinc-950 hover:bg-zinc-800 rounded text-zinc-400">edit</a>
                        </div>
                    </div>

                    <div class="flex items-center gap-3 text-xs mb-3">
                        <span class="text-zinc-400">{m.get('symbol','')} {m.get('timeframe','')}</span>
                        {pnl_html}
                        {tags_html}
                    </div>

                    <!-- Quick status actions (v0.1) -->
                    <div class="flex gap-1.5 mb-2">
                        <form method="post" action="/set-status/{nid}" class="inline">
                            <input type="hidden" name="status" value="idea">
                            <button type="submit" class="text-[10px] px-2 py-0.5 rounded bg-amber-900/40 hover:bg-amber-900/70 text-amber-300">Idea</button>
                        </form>
                        <form method="post" action="/set-status/{nid}" class="inline">
                            <input type="hidden" name="status" value="paper">
                            <button type="submit" class="text-[10px] px-2 py-0.5 rounded bg-blue-900/40 hover:bg-blue-900/70 text-blue-300">Paper</button>
                        </form>
                        <form method="post" action="/set-status/{nid}" class="inline">
                            <input type="hidden" name="status" value="closed">
                            <button type="submit" class="text-[10px] px-2 py-0.5 rounded bg-emerald-900/40 hover:bg-emerald-900/70 text-emerald-300">Closed</button>
                        </form>
                    </div>
                </div>
                """
        else:
            notes_html = '<div class="text-center py-12 text-zinc-500">No notes found for this filter. <a href="/" class="underline">Clear filter</a></div>'

        content = stats_html + export_html + search_html + notes_html
        templates = list_templates()
        return HTMLResponse(Template(BASE_HTML).render(content=content, templates=templates))

    @app.get("/templates", response_class=HTMLResponse)
    def templates_page():
        tpls = list_templates()
        html = "<div class='max-w-2xl'><h2 class='text-2xl font-semibold mb-6'>Available Templates</h2>"
        for t in tpls:
            tpl_content = load_template(t)
            preview = tpl_content[:320] + "..." if len(tpl_content) > 320 else tpl_content
            html += f"""
            <div class="mb-4 bg-zinc-900 border border-zinc-800 rounded-3xl p-5">
                <div class="font-medium mb-2">{t}</div>
                <pre class="text-xs text-zinc-400 whitespace-pre-wrap font-mono">{preview}</pre>
            </div>
            """
        html += "</div>"
        templates = list_templates()
        return HTMLResponse(Template(BASE_HTML).render(content=html, templates=templates))

    @app.get("/edit/{filename}", response_class=HTMLResponse)
    def edit_note(filename: str):
        path = NOTES_DIR / filename
        if not path.exists():
            return HTMLResponse("Note not found", status_code=404)
        
        content = path.read_text()
        note_id = filename.replace(".md", "")

        # Pull metadata (v0.1)
        meta = get_note_meta(note_id) or {"status": "idea", "pnl": {}, "tags": []}
        status = meta.get("status", "idea")
        pnl = meta.get("pnl", {})

        status_badge = {
            "idea": '<span class="px-3 py-1 text-sm rounded-full bg-amber-900/60 text-amber-300">IDEA</span>',
            "paper": '<span class="px-3 py-1 text-sm rounded-full bg-blue-900/60 text-blue-300">PAPER</span>',
            "closed": '<span class="px-3 py-1 text-sm rounded-full bg-emerald-900/60 text-emerald-300">CLOSED</span>',
        }.get(status, status)

        pnl_display = ""
        if pnl.get("result"):
            color = "emerald" if pnl["result"] == "win" else ("red" if pnl["result"] == "loss" else "zinc")
            pnl_display = f'<span class="text-{color}-400 font-medium">{pnl["result"].upper()}</span>  |  R:R {pnl.get("rr", "-")}  |  entry {pnl.get("entry", "-")} → exit {pnl.get("exit", "-")}'
        elif pnl.get("entry"):
            pnl_display = f'entry {pnl.get("entry")} (no exit yet)'

        tags_display = " ".join([f'<span class="text-xs px-2 py-0.5 bg-zinc-800 rounded">#{t}</span>' for t in meta.get("tags", [])]) or '<span class="text-xs text-zinc-500">no tags</span>'

        # Pre-compute selected options for P&L form
        res = pnl.get("result") or ""
        sel_win = "selected" if res == "win" else ""
        sel_loss = "selected" if res == "loss" else ""
        sel_be  = "selected" if res == "breakeven" else ""

        html = f"""
        <div class="max-w-7xl">
            <!-- Metadata bar (v0.1) -->
            <div class="bg-zinc-900 border border-zinc-800 rounded-3xl p-4 mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <div class="flex items-center gap-3">
                    <span class="text-zinc-500 text-xs">STATUS</span> {status_badge}
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-zinc-500 text-xs">P&amp;L</span> <span class="text-zinc-300">{pnl_display or '—'}</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-zinc-500 text-xs">TAGS</span> {tags_display}
                </div>
                <div class="flex-1"></div>
                <div class="flex items-center gap-2 text-xs">
                    <form method="post" action="/set-status/{note_id}" class="flex gap-1">
                        <button name="status" value="idea" class="px-2 py-0.5 rounded bg-amber-900/50 hover:bg-amber-900/80">Idea</button>
                        <button name="status" value="paper" class="px-2 py-0.5 rounded bg-blue-900/50 hover:bg-blue-900/80">Paper</button>
                        <button name="status" value="closed" class="px-2 py-0.5 rounded bg-emerald-900/50 hover:bg-emerald-900/80">Closed</button>
                    </form>
                </div>
            </div>

            <!-- Quick P&L form (v0.1) -->
            <div class="bg-zinc-900 border border-zinc-800 rounded-3xl p-4 mb-6">
                <form method="post" action="/set-pnl/{note_id}" class="flex flex-wrap items-end gap-3 text-sm">
                    <div>
                        <label class="block text-[10px] text-zinc-500 mb-0.5">Entry</label>
                        <input type="text" name="entry" value="{pnl.get('entry') or ''}" class="w-28 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-1.5 text-sm font-mono">
                    </div>
                    <div>
                        <label class="block text-[10px] text-zinc-500 mb-0.5">Exit</label>
                        <input type="text" name="exit" value="{pnl.get('exit') or ''}" class="w-28 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-1.5 text-sm font-mono">
                    </div>
                    <div>
                        <label class="block text-[10px] text-zinc-500 mb-0.5">R:R</label>
                        <input type="text" name="rr" value="{pnl.get('rr') or ''}" class="w-20 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-1.5 text-sm font-mono">
                    </div>
                    <div>
                        <label class="block text-[10px] text-zinc-500 mb-0.5">Result</label>
                        <select name="result" class="bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-1.5 text-sm">
                            <option value="">—</option>
                            <option value="win" {sel_win}>win</option>
                            <option value="loss" {sel_loss}>loss</option>
                            <option value="breakeven" {sel_be}>breakeven</option>
                        </select>
                    </div>
                    <button type="submit" class="ml-2 px-5 py-1.5 bg-white text-zinc-950 rounded-2xl text-sm font-medium">Save P&amp;L</button>
                </form>
            </div>

            <div class="flex items-center justify-between mb-6">
                <div>
                    <div class="font-mono text-sm text-zinc-500">{filename}</div>
                    <div class="text-3xl font-semibold tracking-tight">Edit Note</div>
                </div>
                <div class="flex items-center gap-3">
                    <button onclick="confirmDelete()" 
                            class="px-5 py-2 text-sm rounded-2xl border border-red-900/50 text-red-400 hover:bg-red-950/50 transition-colors">Delete</button>
                    <a href="/" class="px-5 py-2 text-sm rounded-2xl bg-zinc-800 hover:bg-zinc-700 transition-colors">← Back to Notes</a>
                </div>
            </div>

            <form method="post" action="/save/{filename}" id="editForm">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <!-- Editor -->
                    <div>
                        <div class="flex items-center justify-between mb-2 px-1">
                            <div class="text-xs uppercase tracking-widest text-zinc-500">Markdown Source</div>
                            <div class="text-[10px] text-zinc-600">Ctrl+S to save</div>
                        </div>
                        <textarea id="editor" name="content" 
                                  class="w-full h-[620px] bg-zinc-900 border border-zinc-800 rounded-3xl p-6 font-mono text-sm leading-relaxed focus:outline-none focus:border-zinc-700 resize-y"
                                  oninput="updatePreview()">{content}</textarea>
                    </div>

                    <!-- Live Preview -->
                    <div>
                        <div class="text-xs uppercase tracking-widest text-zinc-500 mb-2 px-1">Live Preview</div>
                        <div id="preview" 
                             class="w-full h-[620px] bg-zinc-900 border border-zinc-800 rounded-3xl p-6 overflow-auto prose prose-invert prose-sm max-w-none text-zinc-200">
                        </div>
                    </div>
                </div>

                <div class="mt-6 flex gap-3">
                    <button type="submit" class="px-8 py-3 bg-white text-zinc-950 rounded-2xl font-medium hover:bg-zinc-200 transition-colors">Save Changes</button>
                    <a href="/" class="px-8 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl transition-colors">Cancel</a>
                </div>
            </form>
        </div>

        <!-- Delete Modal -->
        <div id="deleteModal" class="hidden fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div class="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 w-full max-w-sm">
                <div class="font-semibold text-xl mb-2">Delete this note?</div>
                <div class="text-sm text-zinc-400 mb-6">This action cannot be undone. The file will be permanently removed.</div>
                <div class="flex gap-3">
                    <button onclick="hideDeleteModal()" 
                            class="flex-1 py-3 rounded-2xl bg-zinc-800 hover:bg-zinc-700 transition-colors">Cancel</button>
                    <button onclick="performDelete()" 
                            class="flex-1 py-3 rounded-2xl bg-red-600 hover:bg-red-700 text-white font-medium transition-colors">Delete Note</button>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <script>
            function updatePreview() {{
                const source = document.getElementById('editor').value;
                const preview = document.getElementById('preview');
                preview.innerHTML = marked.parse(source);
            }}
            
            function confirmDelete() {{
                document.getElementById('deleteModal').classList.remove('hidden');
                document.getElementById('deleteModal').classList.add('flex');
            }}
            
            function hideDeleteModal() {{
                document.getElementById('deleteModal').classList.add('hidden');
                document.getElementById('deleteModal').classList.remove('flex');
            }}
            
            function performDelete() {{
                window.location.href = '/delete/{filename}';
            }}
            
            // Initial render
            document.addEventListener('DOMContentLoaded', function() {{
                updatePreview();
                
                // Ctrl+S to save
                document.addEventListener('keydown', function(e) {{
                    if (e.ctrlKey && e.key === 's') {{
                        e.preventDefault();
                        document.getElementById('editForm').submit();
                    }}
                }});
            }});
        </script>
        """
        templates = list_templates()
        return HTMLResponse(Template(BASE_HTML).render(content=html, templates=templates))

    @app.post("/save/{filename}")
    async def save_note(filename: str, content: str = Form(...)):
        path = NOTES_DIR / filename
        path.write_text(content)
        return RedirectResponse("/", status_code=303)

    @app.post("/create")
    async def create_from_web(template: str = Form(...), symbol: str = Form(...), timeframe: str = Form(...)):
        create_note(template, symbol, timeframe)
        return RedirectResponse("/", status_code=303)

    @app.get("/delete/{filename}")
    async def delete_note(filename: str):
        path = NOTES_DIR / filename
        if path.exists():
            path.unlink()
        return RedirectResponse("/", status_code=303)

    # === v0.1: Status & P&L updates from web ===
    @app.post("/set-status/{note_id}")
    async def set_status_web(note_id: str, status: str = Form(...)):
        try:
            set_status(note_id, status)
        except Exception as e:
            print(f"Status update error: {e}")
        return RedirectResponse("/", status_code=303)

    @app.post("/set-pnl/{note_id}")
    async def set_pnl_web(note_id: str, entry: str = Form(""), exit: str = Form(""), rr: str = Form(""), result: str = Form("")):
        try:
            updates = {}
            if entry: updates["entry"] = float(entry) if entry else None
            if exit:  updates["exit"]  = float(exit) if exit else None
            if rr:    updates["rr"]    = float(rr) if rr else None
            if result: updates["result"] = result or None
            update_pnl(note_id, **updates)
        except Exception as e:
            print(f"P&L update error: {e}")
        return RedirectResponse(f"/edit/{note_id}.md", status_code=303)

    # === Export routes (v1.0) ===
    @app.get("/export/json")
    async def export_json():
        ensure_notes_dir()
        notes = sorted(NOTES_DIR.glob("*.md"), reverse=True)
        data = []
        for note in notes:
            content = note.read_text()
            symbol_match = re.search(r"Symbol:\s*([A-Z0-9]+)", content)
            symbol = symbol_match.group(1) if symbol_match else "UNKNOWN"
            data.append({
                "filename": note.name,
                "symbol": symbol,
                "content": content
            })
        return {"notes": data, "count": len(data), "exported_at": datetime.now().isoformat()}

    @app.get("/export/all")
    async def export_all_zip():
        import zipfile
        from io import BytesIO
        from fastapi.responses import StreamingResponse

        ensure_notes_dir()
        notes = sorted(NOTES_DIR.glob("*.md"), reverse=True)
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for note in notes:
                zip_file.writestr(note.name, note.read_text())
        
        zip_buffer.seek(0)
        filename = f"msn-notes-{datetime.now().strftime('%Y-%m-%d')}.zip"
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    return app


def serve(port: int = 8765):
    """Start the web viewer (thin wrapper around create_app)."""
    try:
        import uvicorn
    except ImportError:
        print("Web dependencies missing. Install with: pip install 'market-structure-notes[web]'")
        print("This includes FastAPI + python-multipart (needed for the web forms).")
        return

    app = create_app()
    print(f"Starting web viewer on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


def main():
    parser = argparse.ArgumentParser(
        description="Market Structure Notes — structured trading journal (Wyckoff/SMC/ICT)"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__import__('msn').__version__}")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new")
    p_new.add_argument("--template", required=True, choices=list_templates())
    p_new.add_argument("--symbol", required=True)
    p_new.add_argument("--timeframe", required=True)
    p_new.add_argument("--date")

    p_list = sub.add_parser("list")
    p_list.add_argument("--filter", help="Simple text filter on filename")
    p_list.add_argument("--status", choices=["idea", "paper", "closed"], help="Filter by status")
    p_list.add_argument("--symbol", help="Filter by symbol (e.g. BTC)")

    p_search = sub.add_parser("search")
    p_search.add_argument("query")

    p_export = sub.add_parser("export", help="Export notes")
    p_export.add_argument("--format", default="json", choices=["json", "structured", "markdown"],
                          help="json = legacy (raw content only), structured = rich JSON (analysis), markdown = Obsidian/Notion-friendly files with YAML frontmatter")

    p_templates = sub.add_parser("templates")

    # === New v0.1 commands using the metadata store ===
    p_stats = sub.add_parser("stats", help="Show statistics (win rate, counts, etc.)")

    p_status = sub.add_parser("status", help="Change the status of a note")
    p_status.add_argument("note_id", help="Note ID (e.g. 2026-05-29-BTC-4H)")
    p_status.add_argument("new_status", choices=["idea", "paper", "closed"])

    p_pnl = sub.add_parser("pnl", help="Set P&L data on a note")
    p_pnl.add_argument("note_id")
    p_pnl.add_argument("--entry", type=float)
    p_pnl.add_argument("--exit", type=float)
    p_pnl.add_argument("--rr", type=float)
    p_pnl.add_argument("--result", choices=["win", "loss", "breakeven"])

    p_tag = sub.add_parser("tag", help="Add a tag to a note")
    p_tag.add_argument("note_id")
    p_tag.add_argument("tag")

    p_edit = sub.add_parser("edit", help="Edit a note in your $EDITOR (or fallback)")
    p_edit.add_argument("note_id", help="Note ID (e.g. 2026-05-29-BTC-4H)")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()

    if args.cmd == "new":
        create_note(args.template, args.symbol, args.timeframe, args.date)
    elif args.cmd == "list":
        list_notes(args.filter, status=getattr(args, "status", None), symbol=getattr(args, "symbol", None))
    elif args.cmd == "search":
        search_notes(args.query)
    elif args.cmd == "export":
        export_notes(args.format)
    elif args.cmd == "templates":
        print("\n".join(list_templates()))
    elif args.cmd == "stats":
        stats = get_stats()
        perf = stats.get("performance", {})

        print("\n=== Market Structure Notes — Stats (v0.2 analytics) ===\n")

        # High level counts
        print(f"Total notes:      {stats['total_notes']}")
        print(f"By status:        {stats['by_status']}")
        print(f"Paper notes:      {stats.get('paper_notes', 0)}")
        print(f"Closed notes:     {stats['closed_notes']}")
        print(f"By symbol:        {stats['by_symbol']}")
        print(f"By template:      {stats['by_template']}\n")

        # Overall performance
        if stats['closed_notes'] > 0:
            print("--- Closed Trade Performance ---")
            print(f"Wins / Losses / BE:  {perf['wins']} / {perf['losses']} / {perf['breakevens']}")
            print(f"Win rate:            {perf['win_rate']}%")
            if perf.get("avg_rr") is not None:
                print(f"Average R:R:         {perf['avg_rr']}")
            print()

            # By template performance
            if perf.get("by_template"):
                print("--- Performance by Template ---")
                for tpl, p in sorted(perf["by_template"].items(), key=lambda x: -x[1]["closed"]):
                    rr_str = f" | avg RR {p['avg_rr']}" if p.get("avg_rr") else ""
                    print(f"  {tpl:<18} {p['closed']:>2} closed  |  {p['win_rate']:>5.1f}% win{rr_str}")
                print()

            # By symbol performance
            if perf.get("by_symbol"):
                print("--- Performance by Symbol ---")
                for sym, p in sorted(perf["by_symbol"].items(), key=lambda x: -x[1]["closed"]):
                    rr_str = f" | avg RR {p['avg_rr']}" if p.get("avg_rr") else ""
                    print(f"  {sym:<6} {p['closed']:>2} closed  |  {p['win_rate']:>5.1f}% win{rr_str}")
                print()

            # === v0.2 advanced review analytics ===
            review = stats.get("review", {})
            streaks = review.get("streaks", {})
            best = review.get("best_templates", [])

            print("--- Review Analytics ---")
            print(f"Longest win streak:  {streaks.get('longest_win', 0)}")
            print(f"Longest loss streak: {streaks.get('longest_loss', 0)}")
            curr = streaks.get("current", 0)
            curr_str = f"+{curr}" if curr > 0 else str(curr)
            print(f"Current streak:      {curr_str}  (positive = win streak)")
            print()

            if best:
                print("--- Best Performing Templates (by score = win% × avg RR, min 2 trades) ---")
                for b in best:
                    print(f"  {b['template']:<18} {b['closed']:>2} trades  |  {b['win_rate']:>5.1f}%  |  avg RR {b['avg_rr']}  |  score {b['score']}")
                print()
        else:
            print("No closed trades yet. Mark some notes as 'closed' with P&L to see performance analytics.\n")
    elif args.cmd == "status":
        meta = set_status(args.note_id, args.new_status)
        print(f"Updated {args.note_id} → status={meta['status']}")
    elif args.cmd == "pnl":
        meta = update_pnl(
            args.note_id,
            entry=args.entry,
            exit=args.exit,
            rr=args.rr,
            result=args.result,
        )
        print(f"Updated P&L for {args.note_id}: {meta['pnl']}")
    elif args.cmd == "tag":
        meta = add_tag(args.note_id, args.tag)
        print(f"Added tag '{args.tag}' to {args.note_id}. Tags: {meta['tags']}")
    elif args.cmd == "edit":
        edit_note_cli(args.note_id)
    elif args.cmd == "serve":
        serve(args.port)


if __name__ == "__main__":
    main()