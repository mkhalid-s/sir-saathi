#!/usr/bin/env python3
"""Exercise the shared limiter against a disposable Redis service."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.api.privacy import REDIS_URL_ENV, RedisRateLimiter

TEST_KEYS = ("ci-primary", "ci-isolated")


def _fail(blocker: str) -> int:
    print(json.dumps({"passed": False, "blockers": [blocker], "values_redacted": True}, sort_keys=True))
    return 1


def check_redis(redis_url: str) -> dict[str, object]:
    import redis

    client = redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )
    limiter = RedisRateLimiter(client=client, max_requests=2, window_seconds=10)
    full_keys = tuple(f"sir-saathi:rate-limit:{key}" for key in TEST_KEYS)
    try:
        client.delete(*full_keys)
        if not limiter.ready() or any(client.exists(key) for key in full_keys):
            raise RuntimeError("integration.redis_readiness")
        first = limiter.check(TEST_KEYS[0])
        second = limiter.check(TEST_KEYS[0])
        blocked = limiter.check(TEST_KEYS[0])
        isolated = limiter.check(TEST_KEYS[1])
        ttl = client.ttl(full_keys[0])
        if not (
            first.allowed and first.remaining == 1
            and second.allowed and second.remaining == 0
            and not blocked.allowed and blocked.remaining == 0
            and 1 <= blocked.retry_after_seconds <= 10
            and isolated.allowed and isolated.remaining == 1
            and 1 <= ttl <= 10
        ):
            raise RuntimeError("integration.redis_atomic_window")
    finally:
        client.delete(*full_keys)
    if any(client.exists(key) for key in full_keys):
        raise RuntimeError("integration.redis_cleanup")
    return {
        "passed": True,
        "shared_limiter_ready": True,
        "atomic_window_exercised": True,
        "isolated_bucket_exercised": True,
        "test_keys_remaining": 0,
        "values_redacted": True,
    }


def main() -> int:
    redis_url = os.environ.get(REDIS_URL_ENV, "")
    if not redis_url:
        return _fail("integration.redis_url_missing")
    try:
        report = check_redis(redis_url)
    except RuntimeError as error:
        return _fail(str(error))
    except Exception:
        return _fail("integration.redis_operation_failed")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
