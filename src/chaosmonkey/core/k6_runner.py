"""K6 load testing integration without external dependencies."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
import os

# Template assets used to build the embedded dashboard when generated from the runner
TEMPLATE_DIR = Path('reports') / 'k6-dashboard'
TEMPLATE_HTML = TEMPLATE_DIR / 'index.html'
TEMPLATE_CSS = TEMPLATE_DIR / 'styles.css'
TEMPLATE_JS = TEMPLATE_DIR / 'app.js'


class K6Runner:
    """Custom K6 runner that doesn't require chaostoolkit-k6 package."""
    
    def __init__(self) -> None:
        self.k6_binary = self._find_k6()
    
    def _find_k6(self) -> Optional[str]:
        """Find K6 binary in system PATH."""
        try:
            result = subprocess.run(["which", "k6"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        # Try common installation paths
        common_paths = [
            "/usr/local/bin/k6",
            "/opt/homebrew/bin/k6",
            "/usr/bin/k6",
            "/Users/$(whoami)/.local/bin/k6"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
                
        return None
    
    def is_available(self) -> bool:
        """Check if K6 is available on the system."""
        return self.k6_binary is not None
    
    def run_script(
        self,
        script_text: str,
        options: Optional[Dict[str, Any]] = None,
        env: Optional[Dict[str, str]] = None,
        out_json: Optional[Path] = None,
        full: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a K6 script and return results.
        
        Args:
            script_text: The K6 JavaScript code to execute
            options: K6 options to include in the script
            env: Environment variables for the K6 process
            
        Returns:
            Dictionary with execution results
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "K6 binary not found. Please install K6: brew install k6 or npm install -g k6",
                "stdout": "",
                "stderr": "K6 not installed"
            }
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            # Build complete K6 script
            full_script = self._build_k6_script(script_text, options)
            f.write(full_script)
            script_path = f.name
        
        run_result: Dict[str, Any]
        try:
            # Run K6 command
            cmd = [self.k6_binary, "run", script_path]
            # If caller requested JSON output, add appropriate k6 flags
            if out_json is not None:
                # ensure parent dir exists
                try:
                    out_json.parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                if full:
                    cmd += ["--out", f"json={str(out_json)}"]
                else:
                    cmd += [f"--summary-export={str(out_json)}"]

            # Set up environment: copy current environment so PATH and other vars are preserved
            run_env = os.environ.copy()
            if env:
                run_env.update(env)

            # Set K6 web dashboard environment variables for HTML report generation
            # K6_WEB_DASHBOARD_EXPORT prevents hanging by writing to file instead of serving web UI
            if out_json is not None:
                html_report_path = out_json.parent / f"k6-web-dashboard-{out_json.stem}.html"
                run_env['K6_WEB_DASHBOARD'] = 'true'
                run_env['K6_WEB_DASHBOARD_EXPORT'] = str(html_report_path)

            # Calculate appropriate timeout based on script content
            timeout = 600  # Default 10 minutes (increased for stress tests)
            full_script = self._build_k6_script(script_text, options)
            
            # Check for stress test patterns that might need longer timeout
            if 'stages:' in full_script or 'duration:' in full_script:
                # Look for duration patterns and estimate total time
                import re
                durations = re.findall(r"duration: ['\"](\d+[smh])['\"]", full_script)
                if durations:
                    total_seconds = 0
                    for duration in durations:
                        if duration.endswith('s'):
                            total_seconds += int(duration[:-1])
                        elif duration.endswith('m'):
                            total_seconds += int(duration[:-1]) * 60
                        elif duration.endswith('h'):
                            total_seconds += int(duration[:-1]) * 3600
                    # Add 100% buffer time for stress tests (they can be unpredictable)
                    timeout = max(600, int(total_seconds * 2))
                    print(f"[DEBUG] Detected test duration: {total_seconds}s, using timeout: {timeout}s ({timeout/60:.1f}m)")

            # Execute K6 with calculated timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=run_env,
                timeout=timeout
            )

            run_result = {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.stderr if result.returncode != 0 else None
            }

        except subprocess.TimeoutExpired:
            run_result = {
                "success": False,
                "error": f"K6 execution timed out after {timeout} seconds ({timeout/60:.1f} minutes). This may indicate: 1) Target service is slow/unreachable, 2) Network issues, 3) Test duration longer than expected. Consider checking target URL and network connectivity.",
                "stdout": "",
                "stderr": "Timeout"
            }
        except Exception as e:
            run_result = {
                "success": False,
                "error": f"Failed to execute K6: {e}",
                "stdout": "",
                "stderr": str(e)
            }
        finally:
            # Clean up temporary file
            try:
                Path(script_path).unlink()
            except Exception:
                pass

        # After the run completes, try to generate an embedded dashboard HTML
        # and track the k6 web dashboard HTML if it was generated
        try:
            if out_json is not None and out_json.exists():
                try:
                    # Check if k6 web dashboard HTML was generated
                    html_report_path = out_json.parent / f"k6-web-dashboard-{out_json.stem}.html"
                    if html_report_path.exists():
                        # Add web dashboard path to run result
                        run_result['k6_web_dashboard'] = str(html_report_path.absolute())
                    
                    # Try to load payload from out_json. If it's not valid JSON
                    # (e.g. full NDJSON), fall back to embedding raw text under ndjson_raw
                    raw_txt = out_json.read_text(encoding='utf-8')
                    try:
                        payload = json.loads(raw_txt)
                    except Exception:
                        # Non-JSON (likely NDJSON) — embed as raw
                        payload = { 'ndjson_raw': raw_txt }

                    # Also attach execution stdout/stderr for debugging context
                    payload.setdefault('execution_result', {})
                    stdout_combined = run_result.get('stdout') or ''
                    stderr_combined = run_result.get('stderr') or ''
                    if stdout_combined or stderr_combined:
                        payload['execution_result']['raw_output'] = stdout_combined + '\n' + stderr_combined

                    # Build embedded HTML and write to reports/embedded-<stem>.html
                    try:
                        html = self._build_embedded_html(payload)
                        target = Path('reports') / f'embedded-{out_json.stem}.html'
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(html, encoding='utf-8')
                        # Add custom dashboard path to run result
                        run_result['custom_dashboard'] = str(target.absolute())
                    except Exception:
                        # if embedding fails, continue — the run result is still returned
                        pass
                except Exception:
                    pass
        except Exception:
            pass

        return run_result
    
    def _build_k6_script(self, script_text: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Build a complete K6 script with options."""
        import re
        
        parts = []
        
        # Check for existing imports using regex patterns
        http_import_pattern = r"import\s+http\s+from\s+['\"]k6/http['\"]"
        check_import_pattern = r"import\s+\{[^}]*\bcheck\b[^}]*\}\s+from\s+['\"]k6['\"]"
        
        # Add imports only if not already present
        if not re.search(http_import_pattern, script_text):
            parts.append("import http from 'k6/http';")
        if not re.search(check_import_pattern, script_text):
            parts.append("import { check } from 'k6';")
        
        # Add options if provided and not already in script
        if options and "export let options" not in script_text and "export const options" not in script_text:
            options_js = f"export let options = {json.dumps(options, indent=2)};"
            parts.append(options_js)
        
        # Add the main script
        parts.append(script_text)
        
        return "\n\n".join(parts)

    def _load_text(self, p: Path) -> str:
        try:
            return p.read_text(encoding='utf-8') if p.exists() else ''
        except Exception:
            return ''

    def _build_embedded_html(self, k6_json: dict | str) -> str:
        """Build a single-file embedded dashboard HTML using the reports/k6-dashboard template.

        k6_json may be a dict (structured JSON) or a raw NDJSON string.
        """
        html_template = self._load_text(TEMPLATE_HTML)
        css = self._load_text(TEMPLATE_CSS)
        js = self._load_text(TEMPLATE_JS)

        # Inject CSS
        html = html_template.replace('<link rel="stylesheet" href="styles.css" />', f'<style>\n{css}\n</style>')

        # Prepare embedded script
        if isinstance(k6_json, dict):
            ndjson_raw = None
            payload = dict(k6_json)
            if 'ndjson_raw' in payload:
                ndjson_raw = payload.pop('ndjson_raw')

            embedded_json = json.dumps(payload)
            if ndjson_raw is not None:
                raw_escaped = json.dumps(ndjson_raw)
                app_inline = (
                    f"const EMBEDDED_K6_JSON = {embedded_json};\nconst EMBEDDED_K6_RAW = {raw_escaped};\n\n"
                    + js
                    + "\n\n// If an embedded JSON exists, render immediately\nif(typeof EMBEDDED_K6_JSON !== 'undefined' && EMBEDDED_K6_JSON){ try{ renderFromK6Json(EMBEDDED_K6_JSON); renderEmbeddedExecutionResult && renderEmbeddedExecutionResult(EMBEDDED_K6_JSON); }catch(e){ console.error('render error',e) } }\n// If raw NDJSON is present, attempt to parse and render it as well\nif(typeof EMBEDDED_K6_RAW === 'string' && EMBEDDED_K6_RAW.length){ try{ const parsed = tryParseNdjson(EMBEDDED_K6_RAW); renderFromK6Json(parsed); }catch(e){ console.error('NDJSON render error',e) } }"
                )
            else:
                app_inline = (
                    f"const EMBEDDED_K6_JSON = {embedded_json};\nconst EMBEDDED_K6_RAW = null;\n\n"
                    + js
                    + "\n\n// If an embedded JSON exists, render immediately\nif(typeof EMBEDDED_K6_JSON !== 'undefined' && EMBEDDED_K6_JSON){ try{ renderFromK6Json(EMBEDDED_K6_JSON); renderEmbeddedExecutionResult && renderEmbeddedExecutionResult(EMBEDDED_K6_JSON); }catch(e){ console.error('render error',e) } }"
                )
        else:
            raw_escaped = json.dumps(k6_json)
            app_inline = (
                f"const EMBEDDED_K6_JSON = null;\nconst EMBEDDED_K6_RAW = {raw_escaped};\n\n"
                + js
                + "\n\n// If raw embedded NDJSON exists, try to parse and render\nif(typeof EMBEDDED_K6_RAW === 'string' && EMBEDDED_K6_RAW.length){ try{ const parsed = tryParseNdjson(EMBEDDED_K6_RAW); renderFromK6Json(parsed); }catch(e){ console.error('NDJSON render error',e) } }"
            )

        html = html.replace('<script src="app.js"></script>', f'<script>{app_inline}</script>')
        return html


# Create a global instance
k6_runner = K6Runner()


def run_k6_script(script_text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to run K6 scripts.
    This mimics the chaostoolkit-k6 interface.
    """
    return k6_runner.run_script(script_text, options)


def is_k6_available() -> bool:
    """Check if K6 is available."""
    return k6_runner.is_available()