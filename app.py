from __future__ import annotations

import asyncio
import queue
import threading
from dataclasses import dataclass
from typing import Any, Iterator

from flask import Flask, Response, jsonify, render_template, request

from ctg.agent import build_agent, stream_conspiracy_text
from ctg.config import Settings, load_settings

app = Flask(__name__, static_folder="static", template_folder="templates")


@dataclass
class _RuntimeState:
    settings: Settings | None = None
    agent: Any | None = None


_runtime = _RuntimeState()


def _ensure_runtime() -> tuple[Settings, Any]:
    if _runtime.settings is None or _runtime.agent is None:
        _runtime.settings = load_settings()
        _runtime.agent = build_agent(_runtime.settings)
    return _runtime.settings, _runtime.agent


def _format_sse(data: str, event: str | None = None) -> str:
    # SSE: each line of the payload must be prefixed with `data:`.
    body = "".join(f"data: {line}\n" for line in data.split("\n"))
    if event:
        return f"event: {event}\n{body}\n"
    return f"{body}\n"


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/config")
def api_config():
    try:
        settings, _ = _ensure_runtime()
        return jsonify(
            {
                "ok": True,
                "provider": settings.provider,
                "model": settings.model,
            }
        )
    except (RuntimeError, OSError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503


@app.route("/stream")
def stream() -> Response:
    topic = (request.args.get("topic") or "").strip()
    if not topic:
        return Response("Topic query parameter 'topic' is required", status=400)
    if len(topic) > 300:
        return Response("Topic is too long (max 300 characters)", status=400)

    try:
        settings, agent = _ensure_runtime()
    except (RuntimeError, OSError, ValueError) as exc:
        return Response(str(exc), status=503)

    q: queue.Queue[str | None] = queue.Queue()

    async def _produce() -> None:
        try:
            async for token in stream_conspiracy_text(
                topic, settings=settings, agent=agent
            ):
                q.put(_format_sse(token))
            q.put(_format_sse("[DONE]"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Surface any agent/provider failure to the browser as an SSE error event.
            q.put(_format_sse(str(exc), event="error"))
            q.put(_format_sse("[DONE]"))
        finally:
            q.put(None)

    threading.Thread(target=lambda: asyncio.run(_produce()), daemon=True).start()

    def _consume() -> Iterator[str]:
        while True:
            item = q.get()
            if item is None:
                break
            yield item

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return Response(_consume(), mimetype="text/event-stream", headers=headers)


if __name__ == "__main__":
    print("Conspiracy Theory Generator → http://127.0.0.1:5000/")
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
