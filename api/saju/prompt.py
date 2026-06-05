#!/usr/bin/env python3
"""POST /api/saju/prompt — returns the assembled chart + reference context as JSON.

No LLM call. No API key needed. Returns the system prompt and user message
ready to paste into Claude manually.
"""

import importlib.util
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("_saju_api", ROOT / "api" / "saju.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
process_input = _mod.process_input
format_saju = _mod.format_saju

from reading_pipeline.bridge_parser import parse_report
from reading_pipeline.context_selector import select_context
from reading_pipeline.prompt_assembler import assemble_prompt

VALID_FOCUS = {"life", "career", "relationships", "wealth", "year"}


class handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._respond(400, {"error": "Invalid JSON body"})
            return

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
                "longitude":   float(body["longitude"]) if body.get("longitude") is not None else None,
                "utcOffset":   float(body["utcOffset"]) if body.get("utcOffset") is not None else None,
            }
            if input_data["gender"] not in ("M", "F"):
                raise ValueError("gender must be M or F")
        except (KeyError, TypeError, ValueError) as exc:
            self._respond(400, {"error": str(exc)})
            return

        focus = body.get("focus", "life")
        if focus not in VALID_FOCUS:
            focus = "life"
        user_question = str(body["question"]).strip() if body.get("question") else None

        processed = process_input(input_data)
        report_text = format_saju(processed)
        chart = parse_report({"report": report_text})
        ctx = select_context(chart, focus=focus)
        prompt = assemble_prompt(chart, ctx, focus=focus, user_question=user_question)

        self._respond(200, {
            "chart": chart,
            "system_prompt": prompt["system"],
            "user_message": prompt["user"],
        })
