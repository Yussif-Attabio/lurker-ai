"""FastAPI REST and WebSocket backend for the one-room Lurker chat."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from decision_pattern.lurker_gate import OPTIONS, POLICY_DESCRIPTIONS, QUESTION
from eval.publication import load_published_results

from .bedrock_replier import BedrockReplier, MockBedrockReplier
from .config import AppConfig, load_config
from .context import ChatContext
from .metrics import MetricsStore
from .mock_decider import MockDecider
from .pipeline import MessagePipeline
from .schemas import ChatMessage, WebSocketMessage


WEB_DIR = Path(__file__).resolve().parents[2] / "web"


class ConnectionManager:
    """Track WebSocket clients and broadcast one-room events."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections)
        stale: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        if stale:
            async with self._lock:
                for connection in stale:
                    self._connections.discard(connection)


def create_app(
    *,
    config: AppConfig | None = None,
    adapter: Any | None = None,
    replier: Any | None = None,
) -> FastAPI:
    """Create the backend with optional offline test dependencies."""
    manager = ConnectionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        cfg = config or load_config()
        cfg.require_runtime_ready()
        runtime_adapter = adapter
        model_ready = False
        if runtime_adapter is None:
            if cfg.mock_decider:
                runtime_adapter = MockDecider()
            else:
                from .decider_adapter import DeciderAdapter

                runtime_adapter = await asyncio.to_thread(
                    DeciderAdapter,
                    cfg.decider_model_id,
                    cfg.decider_device,
                    cfg.decider_timeout_ms,
                )
        warmup = await asyncio.to_thread(runtime_adapter.warmup)
        model_ready = warmup.error is None

        runtime_replier = replier
        if runtime_replier is None:
            runtime_replier = (
                MockBedrockReplier()
                if cfg.mock_decider
                else BedrockReplier(
                    cfg.bedrock_model_id or "",
                    cfg.aws_region or "",
                    max_calls=cfg.bedrock_max_calls,
                    allowed_latest_text=cfg.bedrock_allowed_latest_text,
                )
            )
        metrics = MetricsStore(cfg.data_dir)
        pipeline = MessagePipeline(
            config=cfg,
            adapter=runtime_adapter,
            replier=runtime_replier,
            context=ChatContext(),
            metrics=metrics,
            broadcast=manager.broadcast,
        )
        app.state.config = cfg
        app.state.pipeline = pipeline
        app.state.metrics = metrics
        app.state.model_ready = model_ready
        try:
            yield
        finally:
            await pipeline.close()

    app = FastAPI(title="Lurker AI", version="0.2.0", lifespan=lifespan)
    app.mount("/assets", StaticFiles(directory=WEB_DIR), name="web-assets")

    @app.middleware("http")
    async def frontend_cache_control(request: Any, call_next: Any) -> Any:
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/health")
    async def health() -> dict[str, object]:
        cfg: AppConfig = app.state.config
        return {
            "status": "ok" if app.state.model_ready else "degraded",
            "decider_mode": "mock" if cfg.mock_decider else "real",
            "model_ready": bool(app.state.model_ready),
        }

    @app.get("/api/about")
    async def about() -> dict[str, object]:
        cfg: AppConfig = app.state.config
        return {
            "question": QUESTION,
            "options": [
                {"action": action, "description": POLICY_DESCRIPTIONS[action]}
                for action in OPTIONS
            ],
            "policy": {
                "context_k": cfg.context_k,
                "reply_threshold": cfg.reply_threshold,
                "react_threshold": cfg.react_threshold,
                "force_reply_on_mention": cfg.force_reply_on_mention,
                "low_confidence": POLICY_DESCRIPTIONS["LOW_CONFIDENCE"],
                "error": POLICY_DESCRIPTIONS["ERROR"],
            },
        }

    @app.get("/api/metrics")
    async def metrics() -> dict[str, object]:
        return app.state.metrics.snapshot()

    @app.get("/api/decisions")
    async def decisions(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
        return [
            event.model_dump(mode="json")
            for event in app.state.metrics.recent(limit)
        ]

    @app.post("/api/reset")
    async def reset() -> dict[str, str]:
        await app.state.pipeline.reset()
        return {"status": "reset", "active_log": str(app.state.metrics.path)}

    @app.get("/api/eval/latest")
    async def eval_latest() -> dict[str, Any]:
        cfg: AppConfig = app.state.config
        try:
            published = load_published_results(cfg.results_dir)
        except ValueError as exc:
            raise HTTPException(
                status_code=503, detail="published evaluation artifact is invalid"
            ) from exc
        if published is None:
            raise HTTPException(status_code=404, detail="no evaluation results found")
        return published

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await manager.connect(websocket)
        try:
            while True:
                payload = await websocket.receive_json()
                try:
                    incoming = WebSocketMessage.model_validate(payload)
                except ValidationError as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": "invalid_message",
                            "detail": exc.errors(include_url=False),
                        }
                    )
                    continue
                message = ChatMessage(sender=incoming.sender, text=incoming.text)
                await app.state.pipeline.process_message(message)
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(websocket)

    return app


app = create_app()
