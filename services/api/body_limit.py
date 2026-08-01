"""Small ASGI request-body boundary applied before JSON parsing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import json
from typing import Any

MAX_API_BODY_BYTES = 16 * 1024
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class BoundedApiBodyMiddleware:
    """Buffer and bound small API bodies before a framework can parse them."""

    def __init__(self, app: ASGIApp, *, max_bytes: int = MAX_API_BODY_BYTES) -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.app = app
        self.max_bytes = max_bytes

    async def _reject(self, send: Send, *, status: int, detail: str) -> None:
        body = json.dumps({"detail": detail}, separators=(",", ":")).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"cache-control", b"no-store"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": body, "more_body": False})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope.get("type") != "http"
            or str(scope.get("method", "GET")).upper() not in BODY_METHODS
            or not str(scope.get("path", "")).startswith("/api/")
        ):
            await self.app(scope, receive, send)
            return

        declared_lengths = [
            value for name, value in scope.get("headers", [])
            if bytes(name).lower() == b"content-length"
        ]
        if len(declared_lengths) > 1:
            await self._reject(send, status=400, detail="Invalid Content-Length")
            return
        if declared_lengths:
            try:
                declared = int(bytes(declared_lengths[0]).decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                await self._reject(send, status=400, detail="Invalid Content-Length")
                return
            if declared < 0:
                await self._reject(send, status=400, detail="Invalid Content-Length")
                return
            if declared > self.max_bytes:
                await self._reject(send, status=413, detail="Request body too large")
                return

        buffered: list[Message] = []
        total = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message.get("type") == "http.disconnect":
                break
            if message.get("type") != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                await self._reject(send, status=413, detail="Request body too large")
                return
            if not message.get("more_body", False):
                break

        position = 0

        async def replay() -> Message:
            nonlocal position
            if position >= len(buffered):
                return {"type": "http.request", "body": b"", "more_body": False}
            message = buffered[position]
            position += 1
            return message

        await self.app(scope, replay, send)
