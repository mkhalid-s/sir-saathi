import asyncio
import json

from services.api.body_limit import BoundedApiBodyMiddleware


def run_request(*, chunks, headers=(), max_bytes=8, path="/api/search", method="POST"):
    app_bodies = []
    sent = []
    messages = [
        {"type": "http.request", "body": body, "more_body": index < len(chunks) - 1}
        for index, body in enumerate(chunks)
    ]

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent.append(message)

    async def app(_scope, replay, app_send):
        body = b""
        while True:
            message = await replay()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        app_bodies.append(body)
        await app_send({"type": "http.response.start", "status": 204, "headers": []})
        await app_send({"type": "http.response.body", "body": b"", "more_body": False})

    middleware = BoundedApiBodyMiddleware(app, max_bytes=max_bytes)
    asyncio.run(middleware({
        "type": "http",
        "method": method,
        "path": path,
        "headers": list(headers),
    }, receive, send))
    return app_bodies, sent, messages


def response(sent):
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    return status, json.loads(body) if body else None


def test_body_limit_rejects_oversized_declared_length_without_reading_body() -> None:
    app_bodies, sent, unread = run_request(chunks=[b"ignored"], headers=[(b"content-length", b"9")])
    assert app_bodies == []
    assert len(unread) == 1
    assert response(sent) == (413, {"detail": "Request body too large"})


def test_body_limit_rejects_chunked_or_underdeclared_oversized_body() -> None:
    app_bodies, sent, _unread = run_request(
        chunks=[b"1234", b"56789"],
        headers=[(b"content-length", b"4")],
    )
    assert app_bodies == []
    assert response(sent) == (413, {"detail": "Request body too large"})


def test_body_limit_replays_an_exact_boundary_body_unchanged() -> None:
    app_bodies, sent, unread = run_request(chunks=[b"123", b"45678"], headers=[(b"content-length", b"8")])
    assert app_bodies == [b"12345678"]
    assert unread == []
    assert response(sent) == (204, None)


def test_body_limit_rejects_ambiguous_or_invalid_content_length() -> None:
    duplicate = run_request(chunks=[b"ok"], headers=[(b"content-length", b"2"), (b"content-length", b"2")])
    invalid = run_request(chunks=[b"ok"], headers=[(b"content-length", b"not-a-number")])
    assert response(duplicate[1]) == (400, {"detail": "Invalid Content-Length"})
    assert response(invalid[1]) == (400, {"detail": "Invalid Content-Length"})


def test_body_limit_does_not_buffer_non_api_routes() -> None:
    app_bodies, sent, unread = run_request(chunks=[b"123456789"], path="/", method="POST")
    assert app_bodies == [b"123456789"]
    assert unread == []
    assert response(sent) == (204, None)
