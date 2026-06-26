from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LLM Agent Supervisor Dashboard</title>
  <style>
    :root { color-scheme: light; font-family: Inter, "Microsoft YaHei", Arial, sans-serif; }
    body { margin: 0; background: #f7f8fa; color: #17202a; }
    header { padding: 20px 28px; background: #ffffff; border-bottom: 1px solid #d7dde5; }
    h1 { margin: 0 0 6px; font-size: 22px; letter-spacing: 0; }
    p { margin: 0; color: #596575; }
    main { padding: 20px 28px 32px; }
    .stats { display: grid; grid-template-columns: repeat(3, minmax(120px, 1fr)); gap: 12px; max-width: 680px; }
    .stat { background: #fff; border: 1px solid #d7dde5; border-radius: 8px; padding: 14px; }
    .stat strong { display: block; font-size: 24px; }
    table { width: 100%; border-collapse: collapse; margin-top: 18px; background: #fff; border: 1px solid #d7dde5; }
    th, td { padding: 10px 12px; border-bottom: 1px solid #e4e8ee; text-align: left; vertical-align: top; font-size: 14px; }
    th { background: #eef2f6; color: #334155; }
    .badge { display: inline-block; min-width: 48px; text-align: center; border-radius: 999px; padding: 3px 8px; font-weight: 700; }
    .allow { background: #dff7e8; color: #136c36; }
    .ask { background: #fff1c7; color: #8a5a00; }
    .block { background: #ffd9dd; color: #9b1c31; }
    code { white-space: pre-wrap; word-break: break-word; }
  </style>
</head>
<body>
  <header>
    <h1>LLM Agent Supervisor Dashboard</h1>
    <p>每秒刷新本地 JSONL 审计日志，展示模型输入、工具调用、文件访问、代码执行和输出过滤记录。</p>
  </header>
  <main>
    <section class="stats">
      <div class="stat"><span>Allow</span><strong id="allow">0</strong></div>
      <div class="stat"><span>Ask</span><strong id="ask">0</strong></div>
      <div class="stat"><span>Block</span><strong id="block">0</strong></div>
    </section>
    <table>
      <thead>
        <tr><th>Case</th><th>Stage</th><th>Tool</th><th>Decision</th><th>Reason</th><th>Preview</th></tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </main>
  <script>
    async function refresh() {
      const response = await fetch('/audit');
      const events = await response.json();
      const counts = { allow: 0, ask: 0, block: 0 };
      for (const event of events) {
        if (counts[event.decision] !== undefined) counts[event.decision] += 1;
      }
      for (const key of Object.keys(counts)) document.getElementById(key).textContent = counts[key];
      const rows = events.slice(-120).reverse().map(event => {
        const decision = event.decision || '';
        const preview = event.redacted_preview || JSON.stringify(event.tool_args || event.tool_result || {}, null, 0);
        return `<tr>
          <td>${escapeHtml(event.case_id || '')}</td>
          <td>${escapeHtml(event.stage || '')}</td>
          <td>${escapeHtml(event.tool || '')}</td>
          <td><span class="badge ${decision}">${escapeHtml(decision)}</span></td>
          <td>${escapeHtml(event.reason || '')}</td>
          <td><code>${escapeHtml(String(preview).slice(0, 320))}</code></td>
        </tr>`;
      }).join('');
      document.getElementById('rows').innerHTML = rows;
    }
    function escapeHtml(value) {
      return value.replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[ch]));
    }
    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    runtime_dir: Path = Path("runtime")

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path == "/" or self.path.startswith("/index"):
            self._send(200, "text/html; charset=utf-8", HTML.encode("utf-8"))
            return
        if self.path.startswith("/audit"):
            events = self._read_events(self.runtime_dir / "audit_log.jsonl")
            self._send(200, "application/json; charset=utf-8", json.dumps(events, ensure_ascii=False).encode("utf-8"))
            return
        self._send(404, "text/plain; charset=utf-8", b"not found")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _read_events(path: Path) -> list[dict]:
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local supervision dashboard.")
    parser.add_argument("--runtime", default=Path(__file__).resolve().parents[1] / "runtime", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8899, type=int)
    args = parser.parse_args()
    args.runtime.mkdir(parents=True, exist_ok=True)
    DashboardHandler.runtime_dir = args.runtime
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"dashboard: http://{args.host}:{args.port}")
    print(f"audit log: {args.runtime / 'audit_log.jsonl'}")
    server.serve_forever()


if __name__ == "__main__":
    main()
