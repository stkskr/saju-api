"""
Master prompt assembler — combines a parsed chart and selected reference
context into a focused prompt for an LLM saju reading.

Architecture:
    parse_report (chart)  →  select_context (refs)  →  assemble_prompt  →  LLM
"""
import json


SYSTEM_PROMPT = """You are a Saju (사주, Korean Four Pillars) reading specialist with deep knowledge of classical Bazi methodology. You provide thoughtful, grounded interpretations of birth charts using the reference library provided.

## Methodology priority — always follow in this order

1. **Day Master assessment** — Use the strength of the day stem in the month branch and its roots in other branches. Reference: yong_sin.md.
2. **Useful god (용신) identification** — Pick from the five strategies (부억, 통관, 병약, 조후, 전왕). The useful god guides everything downstream.
3. **Pattern (격국) identification** — Determine the structural shape of the chart from the month branch.
4. **Pillar-by-pillar interpretation** — Use 근묘화실 framework: Year = childhood/ancestors, Month = youth/parents/career, Day = self/spouse, Hour = late life/children.
5. **Ten god dynamics** — How the sip-sin appear and interact.
6. **Active relationships** — Combinations, clashes, harmonies, punishments present in the chart.
7. **Sin sal layer** — Auspicious and inauspicious stars actually present.
8. **Dae-un (대운) timeline** — Map current and upcoming 10-year cycles to the methodology above.
9. **Current se-un (세운) overlay** — Read the current year through the lens of the rest.

## Style guidelines

- **Anchor every claim** to specific data in the chart or specific reference content. If you reference a sin sal, name it. If you say the day master is weak, explain which factors.
- **Use Korean terms with English explanations.** Example: "Your 용신 (useful god) is water — meaning..."
- **Acknowledge uncertainty.** Saju is a system of tendencies, not predictions. Use language like "this often manifests as," "tends toward," "suggests."
- **Tone:** Experienced practitioner. Neither dismissive nor mystical. Grounded.
- **Length and depth:** Match what the user asked for. A "career reading" should focus on career; a "full life reading" can range broader.
- **Do NOT invent data.** If something isn't in the chart, say so. Don't assume facts about the person beyond what the chart shows.
- **Distinguish character readings (high confidence) from forecast readings (lower confidence).** Character is what is; forecast is what tends to.

## What NOT to do

- Don't recompute the chart — trust the structured data provided.
- Don't list every sin sal in the library — only the ones marked present.
- Don't pad with generic horoscope language. Be specific.
- Don't be fatalistic. The chart shows tendencies; people have agency.
"""


READING_FOCUS_PROMPTS = {
    "life": "Provide a comprehensive life reading covering character, life path, major themes, key transitions visible in the dae-un, and notable patterns. ~800-1200 words.",
    "career": "Focus on career and work: natural talents, ideal vocations based on Day Master and useful god, dynamics with authority (관성), wealth (재성) dynamics, and key career-impacting dae-un periods. ~500-800 words.",
    "relationships": "Focus on romantic and family relationships: spouse palace (day branch), spouse star (Direct Wealth for men / Direct Officer for women) interactions, sin sal affecting partnership, and key dae-un for partnership shifts. ~500-800 words.",
    "wealth": "Focus on wealth dynamics: 재성 (Direct/Indirect Wealth) presence and condition, useful god relation to wealth, wealth pillars in dae-un, and risk factors (clashes with wealth pillars). ~500-800 words.",
    "year": "Focus on the current year (se-un) and the next 1-2 years: how the current year's pillar interacts with the natal chart, what themes are activated, what to watch for. ~400-600 words."
}


def assemble_prompt(chart, context, focus="life", user_question=None):
    """
    Assemble the full prompt that gets sent to the LLM.

    Args:
        chart: parsed chart dict (from bridge_parser.parse_report)
        context: selected reference context (from context_selector.select_context)
        focus: reading scope — life | career | relationships | wealth | year
        user_question: optional specific question to layer on top

    Returns:
        dict with 'system' and 'user' keys (matches Claude/OpenAI message format)
    """

    # ---- SYSTEM ----
    system = SYSTEM_PROMPT

    # ---- USER: assemble the body ----
    parts = []

    # 1. Reading focus
    focus_instructions = READING_FOCUS_PROMPTS.get(focus, READING_FOCUS_PROMPTS["life"])
    parts.append(f"# Reading request\n\n**Focus:** {focus}\n\n{focus_instructions}\n")

    if user_question:
        parts.append(f"**User's specific question:** {user_question}\n")

    # 2. Chart (structured data)
    parts.append("# Chart data\n")
    parts.append("```json")
    parts.append(json.dumps(chart, ensure_ascii=False, indent=2))
    parts.append("```\n")

    # 3. Methodology reference (always included)
    if context.get("methodology"):
        parts.append("# Methodology reference\n")
        parts.append("These primers describe how Saju readings work. Use them as your interpretive framework.\n")
        for item in context["methodology"]:
            parts.append(f"## {item['file']}\n")
            parts.append(item["content"])
            parts.append("")

    # 4. Day Master reference
    if context.get("day_master_ref"):
        parts.append("# Day Master reference\n")
        for item in context["day_master_ref"]:
            parts.append(item["content"])
            parts.append("")

    # 5. Pillar interpretations (the four pillars of THIS chart)
    if context.get("pillars_ref"):
        parts.append("# The four pillars of this chart\n")
        for item in context["pillars_ref"]:
            parts.append(f"## {item['position'].upper()} pillar — {item['jiazi']}\n")
            parts.append(item["content"])
            parts.append("")

    # 6. Ten Gods present
    if context.get("ten_gods_ref"):
        parts.append("# Ten Gods appearing in this chart\n")
        for item in context["ten_gods_ref"]:
            parts.append(item["content"])
            parts.append("")

    # 7. Branches in chart
    if context.get("branches_ref"):
        parts.append("# Branches in this chart\n")
        for item in context["branches_ref"]:
            parts.append(item["content"])
            parts.append("")

    # 8. Relationships active in this chart
    if context.get("relationships_ref"):
        parts.append("# Relationship matrices\n")
        parts.append("These are the active relationships (combinations, clashes, etc.) detected in the chart, plus background tables.\n")
        for item in context["relationships_ref"]:
            parts.append(item["content"])
            parts.append("")

    # 9. Sin sal present
    if context.get("sin_sal_ref"):
        parts.append("# Sin sal stars present in this chart\n")
        for item in context["sin_sal_ref"]:
            parts.append(f"**Location: {item['location']}**\n")
            parts.append(item["content"])
            parts.append("")

    # 10. Elements reference
    if context.get("elements_ref"):
        parts.append("# Five elements reference\n")
        for item in context["elements_ref"]:
            parts.append(item["content"])
            parts.append("")

    # ---- FINAL INSTRUCTION ----
    parts.append("# Now provide the reading\n")
    parts.append("""Walk through the methodology in order. Show your reasoning briefly (1-2 sentences per step), then deliver the reading itself. Use Korean terminology with English explanations. Be specific to THIS chart — never generic.

Begin with a brief chart summary so the reader (and you) can verify accuracy:

> 일주 (Day Pillar): [stem][branch]
> 일간 (Day Master): [stem] - [element] ([yin/yang])
> 월지 (Month Branch): [branch]
> Strength: [strong/weak/balanced]
> 용신 (Useful God): [element]
> 격국 (Pattern): [pattern]

Then proceed with the focused reading.""")

    user = "\n".join(parts)

    return {"system": system, "user": user}


def prompt_stats(prompt):
    """Return token estimates (rough — ~4 chars/token)."""
    system_chars = len(prompt["system"])
    user_chars = len(prompt["user"])
    return {
        "system_chars": system_chars,
        "user_chars": user_chars,
        "total_chars": system_chars + user_chars,
        "approx_tokens": (system_chars + user_chars) // 4,
    }


if __name__ == "__main__":
    from bridge_parser import parse_report
    from context_selector import select_context
    import urllib.request

    req = urllib.request.Request(
        "https://saju-api-eight.vercel.app/api/saju",
        data=json.dumps({"year":1990,"month":5,"day":15,"hour":14,"minute":30,
                         "gender":"F","name":"Test"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        api_response = json.loads(r.read())

    chart = parse_report(api_response)
    ctx = select_context(chart, focus="life")
    prompt = assemble_prompt(chart, ctx, focus="life")
    stats = prompt_stats(prompt)

    print("=== PROMPT STATS ===")
    print(json.dumps(stats, indent=2))
    print("\n=== SYSTEM (first 500 chars) ===")
    print(prompt["system"][:500])
    print("\n=== USER (first 2000 chars) ===")
    print(prompt["user"][:2000])
    print("\n... (truncated) ...")

    # Save full prompt to disk for inspection
    with open("/home/claude/reading_pipeline/example_prompt.txt", "w", encoding="utf-8") as f:
        f.write("=== SYSTEM ===\n")
        f.write(prompt["system"])
        f.write("\n\n=== USER ===\n")
        f.write(prompt["user"])
    print(f"\nFull prompt saved to example_prompt.txt ({stats['total_chars']} chars, ~{stats['approx_tokens']} tokens)")
