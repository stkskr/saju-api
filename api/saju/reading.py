#!/usr/bin/env python3
"""POST /api/saju/reading — streaming LLM Saju reading via Server-Sent Events.

Pipeline:
  1. Compute chart (shared logic from api/saju.py via importlib)
  2. Format text report → bridge_parser → structured chart dict
  3. context_selector picks ~20-25 relevant reference files
  4. Anthropic claude-sonnet-4-6 streams the reading with prompt caching
  5. Events emitted: chart → delta(many) → done
"""

import importlib.util
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from threading import Lock

# Project root: api/saju/reading.py → api/saju → api → root
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

# Load api/saju.py via importlib to share chart logic without Python package conflicts
# (having both api/saju.py and api/saju/ directory prevents normal import)
_spec = importlib.util.spec_from_file_location(
    "_saju_api", ROOT / "api" / "saju.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
process_input = _mod.process_input
format_saju = _mod.format_saju

from reading_pipeline.bridge_parser import parse_report
from reading_pipeline.context_selector import select_context
from reading_pipeline.prompt_assembler import SYSTEM_PROMPT, READING_FOCUS_PROMPTS

import anthropic

# ---------------------------------------------------------------------------
# Rate limiting — in-memory, best-effort (not durable across serverless cold starts)
# For production persistence across instances, swap _rl_store for Upstash Redis.
# ---------------------------------------------------------------------------
_rl_lock = Lock()
_rl_store: dict = defaultdict(lambda: {"minute": [], "day": []})
RATE_PER_MINUTE = 10
RATE_PER_DAY = 50

MODEL = "claude-sonnet-4-6"
VALID_FOCUS = {"life", "career", "relationships", "wealth", "year"}
VALID_LANGUAGE = {"en", "ko", "bilingual"}


def _check_rate_limit(ip: str) -> tuple:
    """Returns (allowed: bool, retry_after_seconds: int)."""
    now = time.time()
    with _rl_lock:
        b = _rl_store[ip]
        b["minute"] = [t for t in b["minute"] if now - t < 60]
        b["day"] = [t for t in b["day"] if now - t < 86400]
        if len(b["minute"]) >= RATE_PER_MINUTE:
            return False, int(60 - (now - b["minute"][0])) + 1
        if len(b["day"]) >= RATE_PER_DAY:
            return False, int(86400 - (now - b["day"][0])) + 1
        b["minute"].append(now)
        b["day"].append(now)
        return True, 0


class handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default access log; structured logging happens via print()

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _client_ip(self) -> str:
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() if fwd else self.client_address[0]

    def _emit(self, payload: dict) -> None:
        line = "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
        self.wfile.write(line.encode("utf-8"))
        self.wfile.flush()

    def _json_error(self, code: int, message: str, error_code: str) -> None:
        """Send a plain JSON error response (used before SSE headers are sent)."""
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(
            json.dumps({"type": "error", "message": message, "code": error_code},
                       ensure_ascii=False).encode("utf-8")
        )

    def do_POST(self):
        req_id = str(uuid.uuid4())
        t0 = time.time()

        # ── 1. Parse request body ──────────────────────────────────────────
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._json_error(400, "Invalid JSON body", "invalid_input")
            return

        # ── 2. Validate ────────────────────────────────────────────────────
        try:
            input_data = {
                "year":        int(body["year"]),
                "month":       int(body["month"]),
                "day":         int(body["day"]),
                "hour":        int(body.get("hour", 0)),
                "minute":      int(body.get("minute", 0)),
                "gender":      str(body["gender"]),
                "name":        str(body.get("name", "")),
                "unknownTime": bool(body.get("unknownTime", False)),
            }
            if input_data["gender"] not in ("M", "F"):
                raise ValueError("gender must be 'M' or 'F'")
        except (KeyError, TypeError, ValueError) as exc:
            self._json_error(400, str(exc), "invalid_input")
            return

        focus = body.get("focus", "life")
        if focus not in VALID_FOCUS:
            self._json_error(
                400,
                f"focus must be one of: {', '.join(sorted(VALID_FOCUS))}",
                "invalid_input",
            )
            return

        language = body.get("language", "en")
        if language not in VALID_LANGUAGE:
            language = "en"

        user_question = str(body["question"]).strip() if body.get("question") else None

        # ── 3. Rate limit ──────────────────────────────────────────────────
        allowed, retry_after = _check_rate_limit(self._client_ip())
        if not allowed:
            self.send_response(429)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Retry-After", str(retry_after))
            self._cors()
            self.end_headers()
            self._emit({
                "type": "error",
                "message": "Rate limit exceeded. Try again shortly.",
                "code": "rate_limit_exceeded",
            })
            return

        # ── 4. SSE response headers ────────────────────────────────────────
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()

        try:
            # ── 5. Compute chart (shared with /api/saju) ───────────────────
            processed = process_input(input_data)
            report_text = format_saju(processed)
            chart = parse_report({"report": report_text})

            # ── 6. Emit chart event ────────────────────────────────────────
            self._emit({"type": "chart", "chart": chart})

            # ── 7. Select relevant reference files (~20-25 files) ──────────
            ctx = select_context(chart, focus=focus)

            # ── 8. Build prompt with caching structure ─────────────────────
            # Block A — cached (reference library, same content for this chart)
            ref_parts = []

            if ctx.get("methodology"):
                ref_parts.append("# Methodology reference\n")
                for item in ctx["methodology"]:
                    ref_parts.append(f"## {item['file']}\n{item['content']}\n")

            if ctx.get("day_master_ref"):
                ref_parts.append("# Day Master reference\n")
                for item in ctx["day_master_ref"]:
                    ref_parts.append(item["content"] + "\n")

            if ctx.get("pillars_ref"):
                ref_parts.append("# Four pillars of this chart\n")
                for item in ctx["pillars_ref"]:
                    ref_parts.append(
                        f"## {item['position'].upper()} pillar — {item['jiazi']}\n"
                        + item["content"] + "\n"
                    )

            if ctx.get("ten_gods_ref"):
                ref_parts.append("# Ten Gods present in this chart\n")
                for item in ctx["ten_gods_ref"]:
                    ref_parts.append(item["content"] + "\n")

            if ctx.get("branches_ref"):
                ref_parts.append("# Branches present in this chart\n")
                for item in ctx["branches_ref"]:
                    ref_parts.append(item["content"] + "\n")

            if ctx.get("relationships_ref"):
                ref_parts.append("# Relationship matrices\n")
                for item in ctx["relationships_ref"]:
                    ref_parts.append(item["content"] + "\n")

            if ctx.get("sin_sal_ref"):
                ref_parts.append("# Sin sal stars present\n")
                for item in ctx["sin_sal_ref"]:
                    ref_parts.append(
                        f"**Location: {item['location']}**\n{item['content']}\n"
                    )

            if ctx.get("elements_ref"):
                ref_parts.append("# Five elements reference\n")
                for item in ctx["elements_ref"]:
                    ref_parts.append(item["content"] + "\n")

            cacheable_reference = "\n".join(ref_parts)

            # Block B — not cached (chart-specific, varies per request)
            focus_instruction = READING_FOCUS_PROMPTS.get(
                focus, READING_FOCUS_PROMPTS["life"]
            )
            tail_parts = [
                f"# Reading request\n\n**Focus:** {focus}\n\n{focus_instruction}\n",
            ]
            if user_question:
                tail_parts.append(f"**User's specific question:** {user_question}\n")
            tail_parts.append(
                "# Chart data\n```json\n"
                + json.dumps(chart, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
            tail_parts.append(
                "# Now provide the reading\n\n"
                "Walk through the methodology in order. Show your reasoning briefly "
                "(1-2 sentences per step), then deliver the reading. "
                "Use Korean terminology with English explanations. "
                "Be specific to THIS chart — never generic.\n\n"
                "Begin with a brief chart summary:\n\n"
                "> 일주 (Day Pillar): [stem][branch]\n"
                "> 일간 (Day Master): [stem] — [element] ([yin/yang])\n"
                "> 월지 (Month Branch): [branch]\n"
                "> Strength: [strong/weak/balanced]\n"
                "> 용신 (Useful God): [element]\n"
                "> 격국 (Pattern): [pattern]\n\n"
                "Then proceed with the focused reading."
            )

            if language == "ko":
                tail_parts.append(
                    "\n\nProvide the entire reading in Korean (한국어로 작성하세요)."
                )
            elif language == "bilingual":
                tail_parts.append(
                    "\n\nProvide the reading bilingually: Korean paragraph first, "
                    "then the English translation immediately below each section."
                )

            non_cacheable_tail = "\n".join(tail_parts)

            # ── 9. Stream Anthropic call with prompt caching ───────────────
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                self._emit({
                    "type": "error",
                    "message": "LLM service unavailable (missing API key)",
                    "code": "internal_error",
                })
                return

            client = anthropic.Anthropic(api_key=api_key)

            full_text = ""
            tokens_used = {}

            with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            # Cacheable: reference library (same across retries / same chart)
                            "type": "text",
                            "text": cacheable_reference,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            # Non-cacheable: chart JSON + focus + question + final instruction
                            "type": "text",
                            "text": non_cacheable_tail,
                        },
                    ],
                }],
            ) as stream:
                for delta in stream.text_stream:
                    full_text += delta
                    self._emit({"type": "delta", "text": delta})

                final_msg = stream.get_final_message()
                u = final_msg.usage
                tokens_used = {
                    "input_tokens":                u.input_tokens,
                    "output_tokens":               u.output_tokens,
                    "cache_read_input_tokens":     getattr(u, "cache_read_input_tokens", 0) or 0,
                    "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
                }

            cached = tokens_used["cache_read_input_tokens"] > 0
            duration_ms = int((time.time() - t0) * 1000)

            # Structured log — no PII (no name, birth data, or reading text)
            print(json.dumps({
                "req": req_id,
                "focus": focus,
                "language": language,
                "tokens": tokens_used,
                "cached": cached,
                "ms": duration_ms,
                "ok": True,
            }), flush=True)

            self._emit({
                "type": "done",
                "reading": full_text,
                "tokens_used": tokens_used,
                "cached": cached,
            })

        except anthropic.APIStatusError as exc:
            ms = int((time.time() - t0) * 1000)
            print(json.dumps({"req": req_id, "ok": False, "code": "llm_error",
                               "status": exc.status_code, "ms": ms}), flush=True)
            self._emit({
                "type": "error",
                "message": "LLM service error. Please try again.",
                "code": "llm_error",
            })

        except anthropic.APITimeoutError:
            ms = int((time.time() - t0) * 1000)
            print(json.dumps({"req": req_id, "ok": False, "code": "llm_error",
                               "reason": "timeout", "ms": ms}), flush=True)
            self._emit({
                "type": "error",
                "message": "LLM request timed out. Please try again.",
                "code": "llm_error",
            })

        except FileNotFoundError as exc:
            ms = int((time.time() - t0) * 1000)
            print(json.dumps({"req": req_id, "ok": False, "code": "internal_error",
                               "missing": str(exc), "ms": ms}), flush=True)
            self._emit({
                "type": "error",
                "message": "Missing reference file in library.",
                "code": "internal_error",
            })

        except Exception as exc:
            ms = int((time.time() - t0) * 1000)
            print(json.dumps({"req": req_id, "ok": False, "code": "internal_error",
                               "detail": type(exc).__name__, "ms": ms}), flush=True)
            self._emit({
                "type": "error",
                "message": "Internal server error.",
                "code": "internal_error",
            })
