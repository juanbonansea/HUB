#!/usr/bin/env python3
"""
Rappi PM Command Center — Local Server with Refresh API
Run: python3 serve.py
Opens at http://localhost:3000
POST /api/refresh → runs Claude Code to pull fresh data and update the HTML
"""
import http.server
import socketserver
import webbrowser
import os
import sys
import json
import subprocess
import threading
import shutil
from datetime import datetime

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(DIRECTORY, "index.html")
REFRESH_LOCK = threading.Lock()
REFRESH_STATUS = {"running": False, "last": None, "error": None}

REFRESH_PROMPT = """You are updating the Rappi PM Hub dashboard at {html_path}.

## Steps:
1. Pull Google Calendar events for the current week (Mon-Fri) using MCP Google Calendar connector. Timezone: America/Bogota. calendarId: primary.
2. Search Gmail for Gemini meeting notes: from:gemini-notes@google.com from the last 7 days. Read each note's content.
3. Search Slack for recent messages to/from juan.bonansea from the last 7 days.
4. Read the current HTML file at {html_path} to understand the data structure (EVENTS, NOTES, DEFAULT_TASKS, DEFAULT_DELEGATED, SLACK_FEED, DEEP_WORK arrays).
5. Edit the HTML file to replace the old data with the fresh data:
   - Update EVENTS with this week's calendar (keep the same structure with day keys mon/tue/wed/thu/fri)
   - Update NOTES with new Gemini notes (extract summaries, sections, action items)
   - Update DEFAULT_TASKS with action items assigned to Juan Pablo
   - Update DEFAULT_DELEGATED with action items for other people
   - Update SLACK_FEED with recent relevant messages
   - Update DEEP_WORK with calculated free blocks
   - Update DAY_DATES and date labels for the current week
   - Update the "Ultima actualizacion" timestamp
6. IMPORTANT: Only edit the data arrays. Do NOT change the HTML structure, CSS, or JavaScript logic.
7. After editing, verify the file is valid by checking it starts with <!DOCTYPE html> and ends with </html>.

Be precise with the edits. Use the Edit tool to replace specific data blocks."""

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        sys.stderr.write(f"  {args[0]}\n")

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_POST(self):
        if self.path == '/api/refresh':
            self.handle_refresh()
        elif self.path == '/api/status':
            self.handle_status()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/api/status':
            self.handle_status()
        else:
            super().do_GET()

    def handle_status(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(REFRESH_STATUS).encode())

    def handle_refresh(self):
        if REFRESH_STATUS["running"]:
            self.send_response(409)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Refresh already running"}).encode())
            return

        # Start refresh in background
        thread = threading.Thread(target=run_refresh, daemon=True)
        thread.start()

        self.send_response(202)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "started"}).encode())


def run_refresh():
    global REFRESH_STATUS
    REFRESH_STATUS = {"running": True, "last": None, "error": None}

    # Find claude CLI
    claude_cmd = shutil.which("claude")
    if not claude_cmd:
        # Common paths including VS Code extension bundled CLI
        import glob
        search_paths = [
            os.path.expanduser("~/.claude/local/claude"),
            "/usr/local/bin/claude",
            os.path.expanduser("~/.local/bin/claude"),
            os.path.expanduser("~/.npm-global/bin/claude"),
        ] + sorted(glob.glob(os.path.expanduser(
            "~/Library/Application Support/Claude/claude-code-vm/*/claude"
        )), reverse=True)  # Latest version first

        for p in search_paths:
            if os.path.isfile(p):
                claude_cmd = p
                break

    if not claude_cmd:
        REFRESH_STATUS = {
            "running": False,
            "last": datetime.now().isoformat(),
            "error": "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
        }
        print("  ERROR: Claude CLI not found")
        return

    prompt = REFRESH_PROMPT.format(html_path=HTML_FILE)
    print(f"  Refreshing via Claude CLI...")

    try:
        result = subprocess.run(
            [claude_cmd, "--print", prompt],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max
            cwd=DIRECTORY
        )
        if result.returncode == 0:
            ts = datetime.now().strftime("%a %d %b, %I:%M%p")
            REFRESH_STATUS = {"running": False, "last": ts, "error": None}
            print(f"  Refresh complete at {ts}")
        else:
            err = result.stderr[:200] if result.stderr else "Unknown error"
            REFRESH_STATUS = {"running": False, "last": datetime.now().isoformat(), "error": err}
            print(f"  Refresh failed: {err}")
    except subprocess.TimeoutExpired:
        REFRESH_STATUS = {"running": False, "last": datetime.now().isoformat(), "error": "Timeout (5min)"}
        print("  Refresh timed out")
    except Exception as e:
        REFRESH_STATUS = {"running": False, "last": datetime.now().isoformat(), "error": str(e)}
        print(f"  Refresh error: {e}")


if __name__ == "__main__":
    os.chdir(DIRECTORY)

    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n  Rappi PM Command Center")
        print(f"  {'─' * 30}")
        print(f"  Running at: {url}")
        print(f"  POST /api/refresh → update data via Claude")
        print(f"  GET  /api/status  → check refresh status")
        print(f"  Press Ctrl+C to stop\n")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.")
            httpd.server_close()
