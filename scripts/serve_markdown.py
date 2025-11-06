#!/usr/bin/env python3
"""Serve Markdown files with Mermaid support.

This is a small, dependency-free local server that serves an index at `/` and a
client-side renderer at `/render/<path>` which fetches the raw Markdown and uses
marked.js and mermaid (via CDN) to render the page in the browser.

By default serves both `docs/` and `reports/` directories. In multi-directory mode,
each directory is mounted at `/<dirname>/` (e.g., `/docs/file.md`, `/reports/file.md`).

Run:
  python3 scripts/serve_markdown.py
  python3 scripts/serve_markdown.py --dir docs --dir reports --port 8000 --bind 127.0.0.1
  python3 scripts/serve_markdown.py --local-js  # for offline usage
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse
import argparse
import os
import html

ROOT_CSS = "https://cdn.jsdelivr.net/npm/github-markdown-css@5.1.0/github-markdown.min.css"
MARKED_JS = "https://cdn.jsdelivr.net/npm/marked/marked.min.js"
MERMAID_JS = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"
VENDOR_DIR = os.path.join(os.path.dirname(__file__), 'vendor')
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reports'))

HTML_TEMPLATE = (
    '<!doctype html>\n'
    '<html>\n'
    '<head>\n'
    '  <meta charset="utf-8">\n'
    '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '  <title>Render: __TITLE__</title>\n'
    f'  <link rel="stylesheet" href="{ROOT_CSS}">\n'
    '  <style>\n'
    '    body { margin: 0; padding: 1rem; background: #f6f8fa; }\n'
    '    .markdown-body { box-sizing: border-box; max-width: 960px; margin: 0 auto; padding: 2rem; background: white; border-radius: 6px; }\n'
    '    pre { background: #0d1117; color: #c9d1d9; padding: 1rem; border-radius: 6px; overflow: auto; }\n'
    '  </style>\n'
    '  <script src="__MARKED_SRC__"></script>\n'
    '  <script src="__MERMAID_SRC__"></script>\n'
    '</head>\n'
    '<body>\n'
    '  <article id="content" class="markdown-body">\n'
    '    <p>Loading <strong>__TITLE__</strong>…</p>\n'
    '  </article>\n'
    '\n'
    '  <script>\n'
    '    async function renderMarkdown(url) {\n'
    '      try {\n'
    '        const resp = await fetch(url);\n'
    '        if (!resp.ok) throw new Error("Failed to fetch: " + resp.status);\n'
    '        const md = await resp.text();\n'
    '        const html = marked.parse(md, { gfm: true, breaks: true });\n'
    '        document.getElementById("content").innerHTML = html;\n'
    '        document.querySelectorAll("pre code").forEach((block) => {\n'
    '          const txt = block.textContent.trim();\n'
    '          if (block.classList.contains("language-mermaid") || txt.startsWith("graph") || txt.startsWith("sequenceDiagram")) {\n'
    '            const wrapper = document.createElement("div");\n'
    '            wrapper.className = "mermaid";\n'
    '            wrapper.textContent = txt;\n'
    '            block.parentElement.replaceWith(wrapper);\n'
    '          }\n'
    '        });\n'
    '        try { mermaid.initialize({ startOnLoad: false }); mermaid.init(undefined, document.querySelectorAll(".mermaid")); } catch (e) { console.warn("mermaid render failed", e); }\n'
    '      } catch (err) {\n'
    '        document.getElementById("content").innerHTML = "<pre style=\\"color:darkred\\">" + err.toString() + "</pre>";\n'
    '      }\n'
    '    }\n'
    '    (function(){ const url = "__URL__"; renderMarkdown(url); })();\n'
    '  </script>\n'
    '</body>\n'
    '</html>\n'
)

INDEX_TEMPLATE = (
    '<!doctype html>\n'
    '<html>\n'
    '<head>\n'
    '  <meta charset="utf-8">\n'
    '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '  <title>Docs index</title>\n'
    '  <style> body { font-family: system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial; padding: 1rem; } a { color: #0366d6; }</style>\n'
    '</head>\n'
    '<body>\n'
    '  <h1>Docs Index</h1>\n'
    '  <ul>\n'
    '    __ITEMS__\n'
    '  </ul>\n'
    '  <p>Render a Markdown file by clicking "view" which opens a client-side renderer with Mermaid support.</p>\n'
    '</body>\n'
    '</html>\n'
)


class RenderHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directories=None, local_js=False, **kwargs):
        # directories: list of directories to serve. If a single dir is
        # provided we preserve legacy behavior (mounted at root). If multiple
        # are provided, each will be mounted at '/<basename>/'.
        self.local_js = bool(local_js)
        dirs = directories or [os.getcwd()]
        # normalize and dedupe
        abs_dirs = [os.path.abspath(d) for d in dirs]
        seen = {}
        mounts = []
        for d in abs_dirs:
            name = os.path.basename(d.rstrip(os.path.sep)) or 'root'
            # resolve duplicates by appending a counter
            orig = name
            i = 1
            while name in seen:
                i += 1
                name = f"{orig}-{i}"
            seen[name] = d
            mounts.append((name, d))
        self.mounts = mounts
        # single-root compatibility
        if len(self.mounts) == 1:
            self.single_root = True
            self.root_dir = self.mounts[0][1]
        else:
            self.single_root = False
            self.root_dir = None
        super().__init__(*args, directory=self.root_dir or os.getcwd(), **kwargs)

    def list_markdown_files(self):
        items = []
        if self.single_root:
            for root, dirs, files in os.walk(self.root_dir):
                for f in sorted(files):
                    if f.lower().endswith('.md'):
                        rel = os.path.relpath(os.path.join(root, f), self.root_dir).replace(os.path.sep, '/')
                        link = '/render/' + rel
                        raw = '/' + rel
                        items.append(f'<li>{html.escape(rel)} — <a href="{link}">view</a> | <a href="{raw}">raw</a></li>')
                break
        else:
            for mount, d in self.mounts:
                prefix = f'{mount}/'
                subitems = []
                for root, dirs, files in os.walk(d):
                    for f in sorted(files):
                        if f.lower().endswith('.md'):
                            rel = os.path.relpath(os.path.join(root, f), d).replace(os.path.sep, '/')
                            link = f'/render/{mount}/{rel}'
                            raw = f'/{mount}/{rel}'
                            subitems.append(f'<li>{html.escape(rel)} — <a href="{link}">view</a> | <a href="{raw}">raw</a></li>')
                    break
                if subitems:
                    items.append(f'<li><strong>/{mount}/</strong><ul>')
                    items.extend(subitems)
                    items.append('</ul></li>')
        return '\n    '.join(items)

    def _find_in_mounts(self, mount, relpath):
        """Return absolute path for a relpath under the named mount, or None."""
        for name, d in self.mounts:
            if name == mount:
                full = os.path.join(d, relpath)
                if os.path.isfile(full):
                    return full
                return None
        return None

    def _find_first(self, relpath):
        """Return the first matching absolute path for relpath across mounts or single_root."""
        if self.single_root:
            full = os.path.join(self.root_dir, relpath)
            return full if os.path.isfile(full) else None
        # search mounts in order
        for name, d in self.mounts:
            full = os.path.join(d, relpath)
            if os.path.isfile(full):
                return full
        return None

    def list_report_files(self):
        items = []
        if not os.path.isdir(REPORTS_DIR):
            return ''
        for root, dirs, files in os.walk(REPORTS_DIR):
            for f in sorted(files):
                if f.lower().endswith('.md') or f.lower().endswith('.json'):
                    rel = os.path.relpath(os.path.join(root, f), REPORTS_DIR).replace(os.path.sep, '/')
                    link = '/render-reports/' + rel
                    raw = '/reports/' + rel
                    items.append(f'<li>{html.escape(rel)} — <a href="{link}">view</a> | <a href="{raw}">raw</a></li>')
            break
        return '\n    '.join(items)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        # Serve local vendor files when requested (used with --local-js)
        if path.startswith('/vendor/'):
            rel = path[len('/vendor/'):]
            safe = os.path.normpath(rel).lstrip('/')
            fullp = os.path.join(VENDOR_DIR, safe)
            if not fullp.startswith(VENDOR_DIR) or not os.path.isfile(fullp):
                self.send_error(404, 'Vendor file not found')
                return
            # serve the file
            ctype = 'application/javascript' if fullp.endswith('.js') else 'application/octet-stream'
            data = open(fullp, 'rb').read()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path == '/' or path == '/index.html':
            body = INDEX_TEMPLATE.replace('__ITEMS__', self.list_markdown_files())
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(body.encode('utf-8'))
            return

        # Reports index
        if path == '/reports' or path == '/reports/' or path == '/reports/index.html':
            items = self.list_report_files()
            body = INDEX_TEMPLATE.replace('__ITEMS__', items)
            # tweak title
            body = body.replace('<h1>Docs Index</h1>', '<h1>Reports Index</h1>')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(body.encode('utf-8'))
            return

        if path.startswith('/render/'):
            target = path[len('/render/'):]
            safe_target = os.path.normpath(target).lstrip('/')
            # If multi-mount, allow /render/<mount>/<rel>
            if not self.single_root and '/' in safe_target:
                mount, rel = safe_target.split('/', 1)
                full = self._find_in_mounts(mount, rel)
                if not full:
                    self.send_error(404, 'File not found')
                    return
                # For multi-mount, the raw URL needs the mount prefix
                url_js = f'/{mount}/{rel}'
            else:
                # single root or a direct relpath
                full = self._find_first(safe_target)
                if not full:
                    self.send_error(404, 'File not found')
                    return
                url_js = '/' + safe_target
            title = html.escape(safe_target)
            body = HTML_TEMPLATE.replace('__TITLE__', title).replace('__URL__', url_js)
            # Choose JS sources: local vendor if requested, otherwise CDN
            if self.local_js:
                marked_src = '/vendor/marked.min.js'
                mermaid_src = '/vendor/mermaid.min.js'
            else:
                marked_src = MARKED_JS
                mermaid_src = MERMAID_JS
            body = body.replace('__MARKED_SRC__', marked_src).replace('__MERMAID_SRC__', mermaid_src)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(body.encode('utf-8'))
            return

        # Render a report (uses the same client-side renderer)
        if path.startswith('/render-reports/'):
            target = path[len('/render-reports/'):]
            safe_target = os.path.normpath(target).lstrip('/')
            full = os.path.join(REPORTS_DIR, safe_target)
            if not full.startswith(REPORTS_DIR) or not os.path.isfile(full):
                self.send_error(404, 'Report not found')
                return
            title = html.escape(safe_target)
            url_js = '/reports/' + safe_target
            body = HTML_TEMPLATE.replace('__TITLE__', title).replace('__URL__', url_js)
            if self.local_js:
                marked_src = '/vendor/marked.min.js'
                mermaid_src = '/vendor/mermaid.min.js'
            else:
                marked_src = MARKED_JS
                mermaid_src = MERMAID_JS
            body = body.replace('__MARKED_SRC__', marked_src).replace('__MERMAID_SRC__', mermaid_src)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(body.encode('utf-8'))
            return

        # Serve raw report files
        if path.startswith('/reports/'):
            rel = path[len('/reports/'):]
            safe = os.path.normpath(rel).lstrip('/')
            fullp = os.path.join(REPORTS_DIR, safe)
            if not fullp.startswith(REPORTS_DIR) or not os.path.isfile(fullp):
                self.send_error(404, 'Report file not found')
                return
            # choose content type
            if fullp.endswith('.md'):
                ctype = 'text/markdown; charset=utf-8'
            elif fullp.endswith('.json'):
                ctype = 'application/json; charset=utf-8'
            else:
                ctype = 'application/octet-stream'
            data = open(fullp, 'rb').read()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        return super().do_GET()


def serve(directories: list | None = None, port: int = 8000, bind: str = '127.0.0.1', local_js: bool = False):
    directories = directories or ['docs', 'reports']
    # validate directories
    abs_dirs = [os.path.abspath(d) for d in directories]
    for d in abs_dirs:
        if not os.path.isdir(d):
            raise SystemExit(f'Directory not found: {d}')
    host = bind
    addr = (host, port)
    handler = lambda *args, **kwargs: RenderHandler(*args, directories=abs_dirs, local_js=local_js, **kwargs)
    with ThreadingHTTPServer(addr, handler) as httpd:
        mounts = ', '.join(directories)
        print(f'Serving {mounts} at http://{host}:{port}/', flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Serve the docs folder with a simple Markdown+Mermaid renderer')
    parser.add_argument('--dir', '-d', action='append', help='Directory to serve (can be specified multiple times). Default: docs, reports')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to listen on (default: 8000)')
    parser.add_argument('--bind', default='127.0.0.1', help='Bind address (default: 127.0.0.1)')
    parser.add_argument('--local-js', action='store_true', help='Serve local vendor JS from scripts/vendor/')
    args = parser.parse_args()
    dirs = args.dir if args.dir else ['docs', 'reports']
    serve(directories=dirs, port=args.port, bind=args.bind, local_js=args.local_js)
