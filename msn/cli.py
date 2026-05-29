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
    ensure_notes_dir()
    results = []
    for note in NOTES_DIR.glob("*.md"):
        if query.lower() in note.read_text().lower():
            results.append(note.name)

    if not results:
        print(f"No matches for '{query}'")
        return

    print(f"Matches for '{query}':")
    for r in results:
        print(f"  {r}")


def export_notes(fmt: str = "json"):
    ensure_notes_dir()
    notes = list(NOTES_DIR.glob("*.md"))
    if not notes:
        print("No notes to export.")
        return

    if fmt == "json":
        data = [{"filename": n.name, "content": n.read_text()} for n in notes]
        out = ROOT / "export.json"
        out.write_text(json.dumps(data, indent=2))
        print(f"Exported {len(notes)} notes to export.json")


def create_app():
    """Create the FastAPI web viewer app (reusable for CLI and previews)."""
    try:
        from fastapi import FastAPI, Form
        from fastapi.responses import HTMLResponse, RedirectResponse
        from jinja2 import Template
    except ImportError:
        raise RuntimeError("Web dependencies missing. Install with: pip install 'market-structure-notes[web]'")

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
    def index(q: str = "", symbol: str = ""):
        ensure_notes_dir()
        all_notes = sorted(NOTES_DIR.glob("*.md"), reverse=True)
        
        # Apply symbol filter first (from clickable pills)
        if symbol:
            all_notes = [n for n in all_notes if f"Symbol: {symbol}" in n.read_text() or f"Symbol:{symbol}" in n.read_text()]
        
        # Then apply text search
        if q:
            all_notes = [n for n in all_notes if q.lower() in n.read_text().lower() or q.lower() in n.name.lower()]
        
        # Build symbol set from ALL notes (not just filtered) for the pills
        all_symbols = set()
        for n in sorted(NOTES_DIR.glob("*.md"), reverse=True):
            m = re.search(r"Symbol:\s*([A-Z0-9]+)", n.read_text())
            if m: all_symbols.add(m.group(1))
        
        # Current active filter display
        filter_pill = ""
        if symbol:
            filter_pill = f'<a href="/" class="inline-flex items-center gap-1 px-3 py-1 bg-white text-zinc-950 text-xs rounded-full font-medium">Filtering: {symbol} <span class="text-zinc-500">×</span></a>'
        
        # Clickable symbol pills
        symbol_pills = ""
        if all_symbols:
            pills = []
            for sym in sorted(all_symbols):
                active = "bg-white text-zinc-950" if sym == symbol else "bg-zinc-800 hover:bg-zinc-700"
                pills.append(f'<a href="/?symbol={sym}" class="px-3 py-1 text-xs rounded-full {active} transition-colors">{sym}</a>')
            symbol_pills = "".join(pills)
        
        stats_html = f"""
        <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="bg-zinc-900 rounded-3xl p-6">
                <div class="text-sm text-zinc-500">Total Notes</div>
                <div class="text-4xl font-semibold mt-2">{len(all_notes)}</div>
            </div>
            <div class="bg-zinc-900 rounded-3xl p-6">
                <div class="text-sm text-zinc-500 mb-2">Symbols Tracked</div>
                <div class="flex flex-wrap gap-1.5">{symbol_pills or '<span class="text-xs text-zinc-500">No symbols yet</span>'}</div>
            </div>
            <div class="bg-zinc-900 rounded-3xl p-6">
                <div class="text-sm text-zinc-500">Templates</div>
                <div class="text-4xl font-semibold mt-2">{len(list_templates())}</div>
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
        if all_notes:
            for note in all_notes:
                content = note.read_text()
                preview = "\n".join(content.split("\n")[:6])
                notes_html += f"""
                <a href="/edit/{note.name}" class="block note-card bg-zinc-900 border border-zinc-800 rounded-3xl p-6 mb-4 hover:border-zinc-700">
                    <div class="flex items-center justify-between mb-4">
                        <div class="font-mono text-sm text-zinc-400">{note.name}</div>
                        <div class="text-xs px-3 py-1 bg-zinc-950 rounded-full text-zinc-500">edit</div>
                    </div>
                    <pre class="text-zinc-300 whitespace-pre-wrap font-mono text-[13px] leading-relaxed bg-black/40 p-4 rounded-2xl overflow-auto">{preview}</pre>
                </a>
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
        html = f"""
        <div class="max-w-7xl">
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
        return

    app = create_app()
    print(f"Starting web viewer on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


def main():
    parser = argparse.ArgumentParser(description="Market Structure Notes")
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

    p_export = sub.add_parser("export")
    p_export.add_argument("--format", default="json", choices=["json"])

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
        print("\n=== Market Structure Notes — Stats ===")
        print(f"Total notes:     {stats['total_notes']}")
        print(f"By status:       {stats['by_status']}")
        print(f"By symbol:       {stats['by_symbol']}")
        print(f"By template:     {stats['by_template']}")
        print(f"Closed notes:    {stats['closed_notes']}")
        print(f"Wins / Losses:   {stats['wins']} / {stats['losses']}")
        print(f"Win rate:        {stats['win_rate']}%\n")
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
    elif args.cmd == "serve":
        serve(args.port)


if __name__ == "__main__":
    main()