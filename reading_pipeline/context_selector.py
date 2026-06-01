"""
Context selector — given a parsed chart, walks the divination/ reference
library and pulls only the files relevant to this specific chart. Keeps the
LLM prompt focused and prevents context bloat.
"""
import json
from pathlib import Path

LIB = Path(__file__).parent.parent / "divination"

# Map ten god ids → expected filename slugs in ten_gods/
# (these depend on what your generator named them — adjust if needed)
TEN_GOD_FILE_MAP = {
    "bi_gyeon":   "bi_jian.md",
    "geop_jae":   "jie_cai.md",
    "sik_sin":    "shi_shen.md",
    "sang_gwan":  "shang_guan.md",
    "jeong_jae":  "zheng_cai.md",
    "pyeon_jae":  "pian_cai.md",
    "jeong_gwan": "zheng_guan.md",
    "pyeon_gwan": "qi_sha.md",
    "jeong_in":   "zheng_yin.md",
    "pyeon_in":   "pian_yin.md",
}

# Interaction type → relationship file
INTERACTION_FILE_MAP = {
    "combination":  "branch_six_combinations.md",
    "clash":        "branch_six_clashes.md",
    "harm":         "branch_six_harms.md",
    "break":        "branch_six_breaks.md",
    "punishment":   "branch_punishments.md",
    "ghost_gate":   None,   # sin sal file, not relationship — fetched separately
    "resentment":   None,
}

# Element id → element file name
ELEMENT_FILES = {"wood": "wood.md", "fire": "fire.md", "earth": "earth.md",
                 "metal": "metal.md", "water": "water.md"}


def _read(path):
    """Read a file from the library; return content or None if missing."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def select_context(chart, focus="life"):
    """
    Build a focused reference context for an LLM prompt.

    Args:
        chart: parsed chart dict (from bridge_parser.parse_report)
        focus: 'life' | 'career' | 'relationships' | 'wealth' | 'year'

    Returns:
        dict with keys: methodology, day_master_ref, pillars_ref, ten_gods_ref,
        branches_ref, relationships_ref, sin_sal_ref, sources
    """
    ctx = {"methodology": [], "day_master_ref": [], "pillars_ref": [],
           "ten_gods_ref": [], "branches_ref": [], "relationships_ref": [],
           "sin_sal_ref": [], "elements_ref": [], "additional": []}

    # 1. METHODOLOGY — always included (these are how readings work)
    for f in ["yong_sin.md", "patterns.md", "geunmyo.md", "dae_un.md"]:
        content = _read(LIB / "saju" / f)
        if content:
            ctx["methodology"].append({"file": f, "content": content})

    # 2. DAY MASTER stem file (most important single reference)
    day_stem_id = chart["day_master"].get("stem_id")
    if day_stem_id:
        # stem files are numbered 01-gap.md through 10-gye.md
        stem_order = ["gap","eul","byeong","jeong","mu","gi","gyeong","sin","im","gye"]
        if day_stem_id in stem_order:
            idx = stem_order.index(day_stem_id) + 1
            f = LIB / "saju" / "stems" / f"{idx:02d}-{day_stem_id}.md"
            content = _read(f)
            if content:
                ctx["day_master_ref"].append({"file": f.name, "content": content})

    # 3. PILLARS — pull all 4 pillar interpretation files
    for pos in ["year", "month", "day", "hour"]:
        if pos not in chart["pillars"]:
            continue
        p = chart["pillars"][pos]
        # Find pillar file by jiazi — they're slugged like 01-gap-ja.md
        # We'll look up by stem_id + branch_id
        # branch_id has special handling for 申 (we used "sin_branch")
        branch_id_for_file = p["branch_id"].replace("sin_branch", "sin")
        # Need to find the actual file in pillars/
        # Use directory listing to find the match
        pillars_dir = LIB / "saju" / "pillars"
        matches = list(pillars_dir.glob(f"*-{p['stem_id']}-{branch_id_for_file}.md"))
        if matches:
            content = _read(matches[0])
            if content:
                ctx["pillars_ref"].append({
                    "position": pos, "jiazi": p["jiazi"],
                    "file": matches[0].name, "content": content
                })

    # 4. TEN GODS — include only those actually appearing in chart
    present_gods = set()
    for pos in chart["pillars"].values():
        for k in ("ten_god_stem", "ten_god_branch"):
            v = pos.get(k)
            if v and v != "day_master":
                present_gods.add(v)
    ten_gods_dir = LIB / "saju" / "ten_gods"
    for god_id in present_gods:
        # Look up the actual filename via the map
        fname = TEN_GOD_FILE_MAP.get(god_id)
        if fname:
            content = _read(ten_gods_dir / fname)
            if content:
                ctx["ten_gods_ref"].append({
                    "god_id": god_id, "file": fname, "content": content
                })

    # 5. BRANCHES — include the 4 branches present in chart
    branch_order = ["ja","chuk","in","myo","jin","sa","o","mi","sin","yu","sul","hae"]
    present_branches = set()
    for pos in chart["pillars"].values():
        bid = pos.get("branch_id", "").replace("sin_branch", "sin")
        if bid:
            present_branches.add(bid)
    for bid in present_branches:
        if bid in branch_order:
            idx = branch_order.index(bid) + 1
            f = LIB / "saju" / "branches" / f"{idx:02d}-{bid}.md"
            content = _read(f)
            if content:
                ctx["branches_ref"].append({
                    "branch_id": bid, "file": f.name, "content": content
                })

    # 6. RELATIONSHIPS — only the files for interaction types in this chart
    interaction_types = set(i["type"] for i in chart["interactions"])
    rel_dir = LIB / "saju" / "relationships"
    for itype in interaction_types:
        fname = INTERACTION_FILE_MAP.get(itype)
        if fname:
            content = _read(rel_dir / fname)
            if content:
                ctx["relationships_ref"].append({
                    "interaction_type": itype, "file": fname, "content": content
                })

    # Also include stem combinations/clashes if they're inferrable (just always include — useful background)
    for fname in ["stem_combinations.md", "stem_clashes.md", "branch_three_harmonies.md"]:
        content = _read(rel_dir / fname)
        if content:
            ctx["relationships_ref"].append({
                "interaction_type": "background", "file": fname, "content": content
            })

    # 7. SIN SAL — only the present ones
    sin_sal_dir = LIB / "saju" / "sin_sal"
    for entry in chart["sin_sal_present"]:
        sid = entry["id"]
        f = sin_sal_dir / f"{sid}.md"
        content = _read(f)
        if content:
            ctx["sin_sal_ref"].append({
                "sin_sal_id": sid, "korean": entry["korean"],
                "location": entry["location"],
                "file": f.name, "content": content
            })

    # 8. ELEMENT FILES — include dominant + missing elements
    counts = chart["five_elements_count"]
    if counts:
        elements_file = _read(LIB / "saju" / "elements.md")
        if elements_file:
            ctx["elements_ref"].append({"file": "elements.md", "content": elements_file})

    # 9. SOURCES (for grounding / citations)
    sources = _read(LIB / "sources.md")
    if sources:
        ctx["additional"].append({"file": "sources.md", "content": sources})

    return ctx


def context_summary(ctx):
    """Quick summary of what was loaded."""
    return {
        "methodology_files": len(ctx["methodology"]),
        "day_master_files": len(ctx["day_master_ref"]),
        "pillar_files": len(ctx["pillars_ref"]),
        "ten_god_files": len(ctx["ten_gods_ref"]),
        "branch_files": len(ctx["branches_ref"]),
        "relationship_files": len(ctx["relationships_ref"]),
        "sin_sal_files": len(ctx["sin_sal_ref"]),
        "element_files": len(ctx["elements_ref"]),
        "additional_files": len(ctx["additional"]),
        "total_files": sum(len(v) for v in ctx.values() if isinstance(v, list)),
        "approx_chars": sum(len(item["content"]) for v in ctx.values()
                            if isinstance(v, list) for item in v)
    }


if __name__ == "__main__":
    from bridge_parser import parse_report
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
    ctx = select_context(chart)
    print(json.dumps(context_summary(ctx), indent=2))
