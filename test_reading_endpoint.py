#!/usr/bin/env python3
"""Integration tests for POST /api/saju/reading.

Usage:
    python test_reading_endpoint.py [BASE_URL]

Defaults to http://localhost:3000. Pass a deployed URL to test production:
    python test_reading_endpoint.py https://saju-api-eight.vercel.app

Tests:
  1. SSE event order: chart → delta(many) → done
  2. Saju terminology present in reading (≥3 of: 일주, 용신, 격국, 대운, 세운)
  3. Cache hit: cache_read_input_tokens > 0 on second identical call
  4. Rate limit: 11 rapid requests → 429 on the 11th
  5. Invalid input → 400
"""

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:3000"
ENDPOINT = f"{BASE_URL}/api/saju/reading"

TEST_PAYLOAD = {
    "year": 1990, "month": 5, "day": 15,
    "hour": 14, "minute": 30,
    "gender": "F", "name": "Test",
    "focus": "life", "language": "en",
}

SAJU_TERMS = ["일주", "용신", "격국", "대운", "세운"]

PASS = "✓"
FAIL = "✗"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post(payload: dict, timeout: int = 120) -> tuple:
    """POST payload to endpoint. Returns (status_code, body_bytes)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _parse_sse(body: bytes) -> list:
    """Parse SSE stream body into a list of event dicts."""
    events = []
    for line in body.decode("utf-8").split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        raise AssertionError(msg)


# ---------------------------------------------------------------------------
# Test 1 — SSE event order and content
# ---------------------------------------------------------------------------

def test_event_order():
    print("Test 1: SSE event order and content...")
    status, body = _post(TEST_PAYLOAD)
    _assert(status == 200, f"Expected HTTP 200, got {status}\nBody: {body[:500]}")

    events = _parse_sse(body)
    _assert(len(events) >= 3, f"Expected ≥3 events, got {len(events)}")

    types = [e.get("type") for e in events]
    _assert(types[0] == "chart",
            f"First event must be 'chart', got '{types[0]}'")

    delta_count = types.count("delta")
    _assert(delta_count > 0, "Expected at least one 'delta' event")
    _assert(types[-1] == "done",
            f"Last event must be 'done', got '{types[-1]}'")

    # chart event shape
    chart_event = events[0]
    _assert("chart" in chart_event, "chart event missing 'chart' field")
    chart = chart_event["chart"]
    _assert("pillars" in chart, "chart missing 'pillars'")
    _assert("day_master" in chart, "chart missing 'day_master'")

    # done event shape
    done_event = events[-1]
    _assert("reading" in done_event, "done event missing 'reading'")
    _assert("tokens_used" in done_event, "done event missing 'tokens_used'")
    _assert("cached" in done_event, "done event missing 'cached'")

    tokens = done_event["tokens_used"]
    for key in ("input_tokens", "output_tokens",
                "cache_read_input_tokens", "cache_creation_input_tokens"):
        _assert(key in tokens, f"tokens_used missing '{key}'")

    reading = done_event["reading"]
    _assert(len(reading) > 200, f"Reading too short: {len(reading)} chars")

    print(f"  {PASS} order: chart → {delta_count} deltas → done")
    print(f"  {PASS} tokens: input={tokens['input_tokens']}, "
          f"output={tokens['output_tokens']}, "
          f"cache_write={tokens['cache_creation_input_tokens']}, "
          f"cache_read={tokens['cache_read_input_tokens']}")
    return done_event


# ---------------------------------------------------------------------------
# Test 2 — Saju terminology
# ---------------------------------------------------------------------------

def test_saju_terminology(done_event: dict):
    print("Test 2: Saju terminology in reading...")
    reading = done_event["reading"]
    found = [t for t in SAJU_TERMS if t in reading]
    _assert(len(found) >= 3,
            f"Expected ≥3 Saju terms in reading, found {len(found)}: {found}\n"
            f"Reading snippet: {reading[:300]}")
    print(f"  {PASS} found terms: {found}")


# ---------------------------------------------------------------------------
# Test 3 — Prompt cache hit on second call
# ---------------------------------------------------------------------------

def test_cache_hit():
    print("Test 3: Prompt cache hit on second identical call...")

    _, body1 = _post(TEST_PAYLOAD)
    events1 = _parse_sse(body1)
    done1 = next((e for e in events1 if e.get("type") == "done"), None)
    _assert(done1 is not None, "First call: no 'done' event received")

    time.sleep(1)  # brief pause between calls

    _, body2 = _post(TEST_PAYLOAD)
    events2 = _parse_sse(body2)
    done2 = next((e for e in events2 if e.get("type") == "done"), None)
    _assert(done2 is not None, "Second call: no 'done' event received")

    cache_read = done2["tokens_used"].get("cache_read_input_tokens", 0)
    _assert(
        cache_read > 0,
        f"Expected cache_read_input_tokens > 0 on second call, got {cache_read}.\n"
        "Note: Anthropic requires ≥1024 tokens in a cacheable block for caching to activate.",
    )
    print(f"  {PASS} cache hit: cache_read_input_tokens={cache_read}")


# ---------------------------------------------------------------------------
# Test 4 — Rate limit: 11 rapid requests → 429 on the 11th+
# ---------------------------------------------------------------------------

def test_rate_limit():
    print("Test 4: Rate limit (11 concurrent requests)...")

    results = []

    def fire(_):
        status, _ = _post(TEST_PAYLOAD, timeout=60)
        return status

    with ThreadPoolExecutor(max_workers=11) as pool:
        futures = [pool.submit(fire, i) for i in range(11)]
        for fut in as_completed(futures):
            results.append(fut.result())

    counts = {}
    for s in results:
        counts[s] = counts.get(s, 0) + 1

    _assert(
        429 in counts,
        f"Expected at least one HTTP 429 after 11 rapid requests. "
        f"Status counts: {counts}\n"
        "Note: in-memory rate limiting may not trigger if requests hit different "
        "serverless instances. Retry against a persistent deployment.",
    )
    print(f"  {PASS} rate limit triggered — status counts: {counts}")


# ---------------------------------------------------------------------------
# Test 5 — Invalid input → 400
# ---------------------------------------------------------------------------

def test_invalid_input():
    print("Test 5: Invalid input → HTTP 400...")

    cases = [
        ({"year": 1990, "gender": "X"},           "missing month/day + bad gender"),
        ({"year": "abc", "month": 5, "day": 15, "gender": "F"}, "non-int year"),
        ({},                                        "empty body"),
    ]

    for payload, label in cases:
        status, _ = _post(payload)
        _assert(status == 400, f"Expected 400 for '{label}', got {status}")
        print(f"  {PASS} {label} → 400")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Endpoint: {ENDPOINT}\n")

    try:
        done_event = test_event_order()
        test_saju_terminology(done_event)
        test_cache_hit()
        test_rate_limit()
        test_invalid_input()
        print(f"\n{PASS} All tests passed.")
        sys.exit(0)
    except AssertionError as exc:
        print(f"\n{FAIL} FAILED: {exc}")
        sys.exit(1)
