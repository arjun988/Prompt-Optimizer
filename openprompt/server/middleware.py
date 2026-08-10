"""FastAPI middleware: API key auth, CORS, rate limiting."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Callable

from openprompt.config.models import ServerConfig


def configure_middleware(app, config: ServerConfig | None = None) -> None:
    cfg = config or ServerConfig.from_env()
    _configure_cors(app, cfg)
    if cfg.api_key:
        _configure_api_key_auth(app, cfg.api_key, set(cfg.public_paths))
    if cfg.rate_limit_per_minute > 0:
        _configure_rate_limit(app, cfg.rate_limit_per_minute)


def _configure_cors(app, config: ServerConfig) -> None:
    try:
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _configure_api_key_auth(app, api_key: str, public_paths: set[str]) -> None:
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next: Callable):
        if request.url.path in public_paths or request.method == "OPTIONS":
            return await call_next(request)
        header_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if header_key != api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key."})
        return await call_next(request)


def _configure_rate_limit(app, limit_per_minute: int) -> None:
    from fastapi import Request
    from fastapi.responses import JSONResponse

    buckets: dict[str, deque[float]] = defaultdict(deque)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable):
        if request.url.path == "/health":
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = buckets[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit_per_minute:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})
        window.append(now)
        return await call_next(request)
