# Local Markdown + Mermaid Renderer

This lightweight script serves Markdown files from your repository with client-side rendering using `marked.js` and `mermaid` for diagrams.

## Quick Start

```bash
# Serve default directories (docs + reports) on localhost:8000
python3 scripts/serve_markdown.py

# Serve specific directories
python3 scripts/serve_markdown.py --dir docs --dir reports

# Custom port and bind address  
python3 scripts/serve_markdown.py --port 8080 --bind 0.0.0.0

# Single directory (legacy mode)
python3 scripts/serve_markdown.py --dir docs
```

## Features

- **Multi-directory support**: By default serves both `docs/` and `reports/` directories
- **Mermaid diagrams**: Automatically renders fenced code blocks with `language-mermaid` or content starting with `graph`/`sequenceDiagram`
- **Offline support**: Use `--local-js` to serve vendor JS files locally
- **Zero dependencies**: Uses only Python standard library
- **Live index**: Browse all Markdown files with "view" and "raw" links

## Directory Mounting

- **Single directory**: Files accessible at root level (e.g., `/file.md`, `/render/file.md`)
- **Multiple directories**: Each mounted at `/<dirname>/` (e.g., `/docs/file.md`, `/reports/file.md`)

## Offline Usage

For environments without internet access, download vendor JS files and use the `--local-js` flag:

```bash
# Download vendor JS files (run once)
curl -o scripts/vendor/marked.min.js https://cdn.jsdelivr.net/npm/marked/marked.min.js
curl -o scripts/vendor/mermaid.min.js https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js

# Run server with local JS
python3 scripts/serve_markdown.py --local-js
```

Expected vendor file locations:
- `scripts/vendor/marked.min.js`
- `scripts/vendor/mermaid.min.js`

## Routes

- `/` - Index of all Markdown files across mounted directories
- `/render/<path>` - Client-side rendered view of Markdown file
- `/<mount>/<path>` - Raw Markdown file content
- `/reports` - Index of reports (when reports directory is mounted)
- `/render-reports/<path>` - Rendered report files
- `/vendor/<file>` - Local vendor JS files (when using `--local-js`)

## Security Note

This is a development server intended for local use. Do not expose to untrusted networks without proper security review.
- If you'd like a version that exports PNG/SVG for Mermaid diagrams or a version that uses a headless renderer, I can add that next.