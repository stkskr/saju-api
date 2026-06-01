# Saju reading pipeline

A three-step pipeline that turns birth info into a focused LLM prompt for accurate Saju readings, using the `divination/` reference library.

```
[Birth info]
    ↓
[saju-api]  ← currently returns text report; recommend adding `chart` JSON
    ↓
[bridge_parser.py]  ← parses text report into structured chart (bridge until API emits JSON)
    ↓
[context_selector.py]  ← selects ~20-25 relevant reference files from the 217-file library
    ↓
[prompt_assembler.py]  ← assembles system + user prompt for the LLM
    ↓
[LLM]  ← Claude / GPT / etc.
    ↓
[Reading]
```

## Why this architecture

**The naive approach** — dump the API report + all 217 ref files into an LLM prompt — has three problems:
1. ~150K tokens of context = expensive, slow, and the model loses focus
2. The LLM has to parse the text report to extract values (fragile)
3. No methodology guidance = inconsistent readings

**This approach** solves all three:
1. Selective retrieval → ~10K-15K token prompts (10x cheaper)
2. Structured chart data → LLM uses it as facts, doesn't re-derive
3. Methodology primers (용신, 격국, 대운, 근묘) always included → consistent reasoning

## Files

| File | Purpose |
|------|---------|
| `bridge_parser.py` | Converts API text report → structured chart dict |
| `context_selector.py` | Walks `divination/` library, picks files matching chart contents |
| `prompt_assembler.py` | Combines chart + context into final LLM prompt |
| `api_response_spec.md` | Proposed JSON schema for your API to emit natively |
| `example_prompt.txt` | Sample assembled prompt for the test chart |

## Usage

```python
import urllib.request, json
from bridge_parser import parse_report
from context_selector import select_context
from prompt_assembler import assemble_prompt

# 1. Hit your API
req = urllib.request.Request(
    "https://saju-api-eight.vercel.app/api/saju",
    data=json.dumps({"year":1990,"month":5,"day":15,"hour":14,
                     "minute":30,"gender":"F","name":"Test"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as r:
    api_response = json.loads(r.read())

# 2. Parse into structured form
chart = parse_report(api_response)

# 3. Pull relevant reference files
context = select_context(chart, focus="life")  # or "career" / "relationships" / "wealth" / "year"

# 4. Build the prompt
prompt = assemble_prompt(chart, context, focus="life",
                          user_question="What career path suits me?")

# 5. Send to LLM
# (your LLM call here — pass prompt["system"] as system, prompt["user"] as user message)
```

## Key design decisions

### Selective context > giant context
For each chart, we only load:
- 4 methodology primers (always)
- 1 day master stem file
- 4 pillar interpretation files
- 3-5 ten god files (only those present in chart)
- 4 branch files (only those in chart)
- 4-8 relationship files (only types detected + background tables)
- 1-3 sin sal files (only those marked present)

That's ~20-25 files instead of all 217. Token cost drops ~10x. Reading accuracy improves because the model isn't drowning in irrelevant data.

### Methodology priority order baked into system prompt
The system prompt enforces the order: Day Master → 용신 → 격국 → pillar interpretation → sip-sin → relationships → sin sal → dae-un → se-un. This is the order classical schools teach. Without it, LLMs tend to jump to surface details (sin sal sound exotic, so models over-weight them).

### Reading focus modes
Five preset focuses bias the prompt: `life | career | relationships | wealth | year`. Each adjusts the final instruction to weight different chart features. You can add more.

### Trust the API's computations
The system prompt explicitly tells the LLM: "Don't recompute the chart — trust the structured data." This is critical because LLMs are bad at the arithmetic (counting elements, computing dae-un dates) but good at interpretation.

## What to do next

### Short-term (works today)
Use the bridge parser. It's fragile (depends on text format) but functional.

### Better — modify your API to emit structured JSON
See `api_response_spec.md` for the proposed schema. Once your API emits `chart` as JSON natively, you can drop `bridge_parser.py` entirely and the pipeline becomes:
```
API → context_selector → prompt_assembler → LLM
```

### Best — prompt caching
The reference library content is *identical across every reading*. Use Anthropic's prompt caching (or equivalent) to cache the methodology + library sections. Cost drops another 5-10x and latency improves significantly. The chart-specific portion is the only part that varies.

## Caveats and limitations

- **Bridge parser is fragile.** It depends on the current text format of your API. Any layout change breaks it. Move to structured JSON ASAP.
- **Sin sal filename inconsistency.** Original 10 sin sal in the library use Chinese pinyin (tian_de_gui_ren), additional 20 use Korean (cheon_eul_gwi_in). Bridge parser handles this but it's worth normalizing the library at some point.
- **Yong sin / pattern not yet computed by API.** Currently the LLM has to derive these from the chart. Your API could pre-compute them deterministically and pass them in — would dramatically improve consistency. See `api_response_spec.md` for the proposed `yong_sin` and `pattern` fields.
- **No prompt streaming yet.** For a UX where the user watches the reading appear, use the LLM's streaming API.
- **Hour pillar assumes Korea local time.** If supporting global users, add timezone handling on the API side.

## Token economics

For a typical reading:
- Input prompt: ~10K-15K tokens
- Output reading: ~5-10K tokens
- Total per reading: ~15-25K tokens
- With prompt caching: input drops to ~2-3K effective tokens (huge savings)

At Claude Sonnet 4 prices (~$3/1M input, $15/1M output), a single reading costs roughly $0.10-0.20 without caching, $0.03-0.08 with caching.
