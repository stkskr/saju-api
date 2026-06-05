# saju-api

Korean Four Pillars (사주) calculation API with an LLM-powered reading endpoint.

Deployed at: `https://saju-api-eight.vercel.app`

---

## Endpoints

### `POST /api/saju` — Chart computation (unchanged)

Returns a formatted text report of the birth chart.

**Request**
```json
{
  "year": 1990, "month": 5, "day": 15,
  "hour": 14, "minute": 30,
  "gender": "F",
  "name": "Optional Name",
  "longitude": -123.1207,
  "utcOffset": -7
}
```

**Response**
```json
{ "report": "═══ SAJU READING ..." }
```

---

### `POST /api/saju/reading` — Streaming LLM reading (new)

Computes the birth chart, selects relevant reference files from the `divination/` library, and streams a personalized Saju reading via [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events).

**Request**
```json
{
  "year": 1990,
  "month": 5,
  "day": 15,
  "hour": 14,
  "minute": 30,
  "gender": "F",
  "name": "Test",
  "focus": "life",
  "question": "What career path suits me?",
  "language": "en"
}
```

| Field | Type | Required | Values | Default |
|---|---|---|---|---|
| `year` | int | ✓ | | |
| `month` | int | ✓ | 1–12 | |
| `day` | int | ✓ | 1–31 | |
| `hour` | int | | 0–23 | `0` |
| `minute` | int | | 0–59 | `0` |
| `gender` | string | ✓ | `M` \| `F` | |
| `name` | string | | | `""` |
| `longitude` | float | | Degrees E (positive) / W (negative) | none |
| `utcOffset` | float | | Hours from UTC, e.g. `-7` for PDT | none |
| `focus` | string | | `life` \| `career` \| `relationships` \| `wealth` \| `year` | `life` |
| `question` | string | | Any follow-up question | none |
| `language` | string | | `en` \| `ko` \| `bilingual` | `en` |

> **True Solar Time (LMT):** When both `longitude` and `utcOffset` are provided, the API converts your local civil time to Local Mean Time before computing pillars. Each degree of longitude = 4 minutes of solar time. Without these fields the API falls back to legacy KDT→KST behaviour (assumes Korean birth).

**Response — `Content-Type: text/event-stream`**

Each event is `data: {...}\n\n`. Events arrive in this order:

```
data: {"type": "chart", "chart": {...}}

data: {"type": "delta", "text": "Your day master..."}
data: {"type": "delta", "text": " is 壬 (water)..."}
... (many delta events)

data: {"type": "done", "reading": "...full text...", "tokens_used": {...}, "cached": true}
```

On any error:
```
data: {"type": "error", "message": "...", "code": "invalid_input|rate_limit_exceeded|llm_error|internal_error"}
```

**curl example (streaming)**
```bash
curl --no-buffer -X POST https://saju-api-eight.vercel.app/api/saju/reading \
  -H "Content-Type: application/json" \
  -d '{"year":1990,"month":5,"day":15,"hour":14,"minute":30,"gender":"F","name":"Test","focus":"life"}'
```

**JavaScript EventSource example**
```js
const res = await fetch('/api/saju/reading', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ year: 1990, month: 5, day: 15, hour: 14, minute: 30, gender: 'F' }),
});
const reader = res.body.getReader();
// decode and split on "\n\n", parse each "data: {...}" line
```

---

### `POST /api/saju/prompt` — Prompt assembly (no LLM)

Returns the fully assembled chart data and reference context as JSON — ready to paste directly into Claude. No API key required.

**Request** — same fields as `/api/saju/reading` (including `longitude`/`utcOffset`)

**Response**
```json
{
  "chart": { ... },
  "system_prompt": "You are a Korean Four Pillars...",
  "user_message": "# Reference library\n..."
}
```

**Example — Vancouver birth (true solar time)**
```json
{
  "year": 1994, "month": 8, "day": 23,
  "hour": 10, "minute": 35,
  "gender": "M",
  "longitude": -123.1207,
  "utcOffset": -7,
  "focus": "life"
}
```

---

## Rate limits

`/api/saju/reading` only (does not apply to `/api/saju`):

| Window | Limit |
|---|---|
| Per minute (per IP) | 10 requests |
| Per day (per IP) | 50 requests |

On limit: HTTP 429 with `Retry-After` header and an SSE error event.

> **Note:** Rate limiting is in-memory. Across serverless cold starts or multiple instances it is best-effort. For strict enforcement, replace `_rl_store` in `api/saju/reading.py` with Upstash Redis.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✓ | Your Anthropic API key. Set in Vercel project settings. Never commit to source. |

---

## Architecture

```
POST /api/saju/reading
         │
         ▼
  process_input()          ← shared with /api/saju (loaded via importlib)
         │
         ▼
  format_saju() → bridge_parser.parse_report()
         │
         ▼
  context_selector.select_context()   ← picks ~20-25 files from divination/
         │
         ▼
  Anthropic claude-sonnet-4-6 (streaming)
    system:  SYSTEM_PROMPT          [cached]
    user[0]: reference library      [cached, ephemeral]
    user[1]: chart JSON + question  [not cached]
         │
         ▼
  SSE stream → client
```

**Prompt caching:** The system prompt and reference library block carry `cache_control: {type: "ephemeral"}`. On repeated calls within 5 minutes the cached tokens are replayed at ~10% cost. Verify via `cache_read_input_tokens > 0` in the `done` event.

**Model:** `claude-sonnet-4-6`. Haiku is intentionally avoided — Saju interpretation requires careful multi-step reasoning over dense classical material.

---

## Reference library

`divination/` — 217 markdown files organized as:

```
divination/
  saju/
    stems/          10 heavenly stems
    branches/       12 earthly branches
    pillars/        60 jiazi pillar interpretations
    ten_gods/       10 sip-sin files
    sin_sal/        30 auspicious/inauspicious stars
    relationships/   9 interaction matrices
    yong_sin.md     useful-god methodology primer
    patterns.md     격국 pattern primer
    geunmyo.md      근묘화실 framework
    dae_un.md       대운 luck cycle primer
    elements.md     five elements reference
  iching/
    hexagrams/      64 hexagrams
    trigrams/        8 trigrams
  sources.md        classical text provenance
```

Only the ~20-25 files relevant to the specific chart are loaded per request.

---

## Running tests

```bash
# Against local Vercel dev server (vercel dev)
python test_reading_endpoint.py

# Against production
python test_reading_endpoint.py https://saju-api-eight.vercel.app
```

Tests: event order, Saju terminology, prompt cache hit, rate limit (11→429), invalid input.
