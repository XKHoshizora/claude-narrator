"""Minimal web UI for monitoring the narrator daemon."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from claude_narrator.config import load_config

logger = logging.getLogger(__name__)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Claude Narrator</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:#0d1117;color:#c9d1d9;padding:24px;max-width:900px;margin:0 auto}
h1{color:#58a6ff;margin-bottom:16px;font-size:1.5rem}
h2{color:#8b949e;font-size:1rem;margin:16px 0 8px;text-transform:uppercase;letter-spacing:0.05em}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.status{display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.85rem;font-weight:600}
.status.running{background:#238636;color:#fff}
.status.stopped{background:#da3633;color:#fff}
table{width:100%;border-collapse:collapse}
td{padding:6px 0;border-bottom:1px solid #21262d}
td:first-child{color:#8b949e;width:120px}
.event{padding:8px 12px;margin:4px 0;border-radius:6px;background:#161b22;
border-left:3px solid #30363d;font-size:0.9rem;display:flex;justify-content:space-between}
.event.high{border-left-color:#da3633}
.event.medium{border-left-color:#d29922}
.event.low{border-left-color:#238636}
.event .time{color:#8b949e;font-size:0.8rem}
#events{max-height:500px;overflow-y:auto}
footer{margin-top:24px;color:#484f58;font-size:0.8rem;text-align:center}
</style>
</head>
<body>
<h1>Claude Narrator</h1>
<div class="card" id="status-card"></div>
<h2>Configuration</h2>
<div class="card"><table id="config-table"></table></div>
<h2>Recent Events</h2>
<div id="events"></div>
<footer>Claude Narrator Web UI &middot; Auto-refreshes every 2s</footer>
<script>
async function refresh(){
try{
const r=await fetch('/api/status');
const d=await r.json();
// Status
const sc=document.getElementById('status-card');
sc.innerHTML=`<span class="status running">Running</span>`;
// Config
const ct=document.getElementById('config-table');
ct.innerHTML=Object.entries(d.config.general||{}).map(([k,v])=>
`<tr><td>${k}</td><td>${v}</td></tr>`).join('')
+`<tr><td>engine</td><td>${d.config.tts?.engine||'-'}</td></tr>`
+`<tr><td>voice</td><td>${d.config.tts?.voice||'-'}</td></tr>`;
// Events
const ev=document.getElementById('events');
ev.innerHTML=(d.events||[]).reverse().map(e=>
`<div class="event ${e.priority}"><span>${e.text}</span><span class="time">${e.time}</span></div>`
).join('')||'<div style="color:#484f58">No events yet</div>';
}catch(e){
document.getElementById('status-card').innerHTML='<span class="status stopped">Unreachable</span>';
}
}
refresh();setInterval(refresh,2000);
</script>
</body>
</html>"""


class WebUI:
    """Simple web UI server for daemon monitoring."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19822) -> None:
        self._host = host
        self._port = port
        self._events: list[dict[str, Any]] = []
        self._server: asyncio.Server | None = None
        self._config: dict[str, Any] = {}

    def set_config(self, config: dict[str, Any]) -> None:
        self._config = config

    def add_event(self, text: str, priority: str = "low") -> None:
        self._events.append({
            "time": time.strftime("%H:%M:%S"),
            "text": text,
            "priority": priority,
        })
        if len(self._events) > 100:
            self._events.pop(0)

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, self._host, self._port
        )
        logger.info("Web UI available at http://%s:%d", self._host, self._port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await reader.read(4096)
            request = data.decode("utf-8", errors="replace")
            first_line = request.split("\r\n", 1)[0] if request else ""

            if "GET /api/status" in first_line:
                body = json.dumps({
                    "config": self._config,
                    "events": self._events[-50:],
                })
                response = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: application/json\r\n"
                    f"Access-Control-Allow-Origin: *\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    f"\r\n{body}"
                )
            else:
                body = HTML_PAGE
                response = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                    f"\r\n{body}"
                )

            writer.write(response.encode("utf-8"))
            await writer.drain()
        except Exception as e:
            logger.debug("Web UI handler error: %s", e)
        finally:
            writer.close()
            await writer.wait_closed()
