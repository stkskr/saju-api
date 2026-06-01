"""
Bridge parser — converts the current saju-api text report into the proposed
structured `chart` JSON. Once your API emits structured data natively, this
file goes away.

Usage:
    from bridge_parser import parse_report
    chart = parse_report(api_response_dict)
"""
import re

# Mapping tables — match what the API outputs to canonical ids in our reference library
STEM_KO_TO_ID = {"갑": "gap", "을": "eul", "병": "byeong", "정": "jeong",
                 "무": "mu",  "기": "gi",  "경": "gyeong", "신": "sin",
                 "임": "im",  "계": "gye"}
STEM_CH_TO_ID = {"甲": "gap", "乙": "eul", "丙": "byeong", "丁": "jeong",
                 "戊": "mu",  "己": "gi",  "庚": "gyeong", "辛": "sin",
                 "壬": "im",  "癸": "gye"}
STEM_ELEM = {"gap": ("wood","yang"), "eul": ("wood","yin"),
             "byeong": ("fire","yang"), "jeong": ("fire","yin"),
             "mu": ("earth","yang"), "gi": ("earth","yin"),
             "gyeong": ("metal","yang"), "sin": ("metal","yin"),
             "im": ("water","yang"), "gye": ("water","yin")}

BRANCH_CH_TO_ID = {"子":"ja","丑":"chuk","寅":"in","卯":"myo","辰":"jin","巳":"sa",
                   "午":"o","未":"mi","申":"sin_branch","酉":"yu","戌":"sul","亥":"hae"}
BRANCH_INFO = {
    "ja":   ("water","rat",     ["癸"]),
    "chuk": ("earth","ox",      ["己","癸","辛"]),
    "in":   ("wood","tiger",    ["甲","丙","戊"]),
    "myo":  ("wood","rabbit",   ["乙"]),
    "jin":  ("earth","dragon",  ["戊","乙","癸"]),
    "sa":   ("fire","snake",    ["丙","庚","戊"]),
    "o":    ("fire","horse",    ["丁","己"]),
    "mi":   ("earth","sheep",   ["己","丁","乙"]),
    "sin_branch": ("metal","monkey", ["庚","壬","戊"]),
    "yu":   ("metal","rooster", ["辛"]),
    "sul":  ("earth","dog",     ["戊","辛","丁"]),
    "hae":  ("water","pig",     ["壬","甲"]),
}

# Ten god labels — Korean → canonical id (matches divination/ files)
TEN_GOD_KO_TO_ID = {
    "비견": "bi_gyeon", "비겁": "bi_gyeon",       # Friend / sometimes API uses 비겁 for both
    "겁재": "geop_jae",                          # Rob Wealth
    "식신": "sik_sin",                           # Food God / Eating God
    "상관": "sang_gwan",                         # Hurting Officer
    "정재": "jeong_jae",                         # Direct Wealth
    "편재": "pyeon_jae",                         # Indirect Wealth
    "정관": "jeong_gwan",                        # Direct Officer
    "편관": "pyeon_gwan", "칠살": "pyeon_gwan",  # Seven Killings
    "정인": "jeong_in",                          # Direct Resource
    "편인": "pyeon_in",                          # Indirect Resource
    "일간": "day_master", "본원": "day_master",
}

# Sin sal Korean → canonical id (must match divination/saju/sin_sal/ filenames)
# Note: original 10 sin sal files use Chinese pinyin, additional 20 use Korean — map accordingly
SIN_SAL_KO_TO_ID = {
    "천을귀인": "cheon_eul_gwi_in",
    "천덕귀인": "tian_de_gui_ren",
    "월덕귀인": "wol_deok_gwi_in",
    "문창귀인": "wen_chang_gui_ren",
    "양인":     "yang_ren",
    "도화":     "tao_hua",
    "금여":     "geum_yeo",
    "백호":     "baek_ho_sal",
    "괴강":     "goe_gang_sal",
    "홍염":     "hong_yeom",  # not in lib but kept for completeness
    "역마":     "yi_ma",
    "화개":     "hua_gai",
    "장성":     "jiang_xing",
    "겁살":     "jie_sha",
    "망신":     "wang_shen",
}

# 12 stage Korean → id
STAGE_KO_TO_ID = {
    "장생":"jangsaeng","목욕":"mogyok","관대":"gwandae","임관":"imgwan",
    "건록":"imgwan",  # API uses 건록 for 임관 sometimes
    "제왕":"jewang","쇠":"soe","병":"byeong","사":"sa","묘":"myo",
    "절":"jeol","태":"tae","양":"yang_stage","공":"gong"
}

# Interaction text → canonical type
INTERACTION_PATTERNS = [
    (r"合\(Combine\)\s*→\s*(\w+)", "combination"),  # combination with element
    (r"沖\(Clash\)",                "clash"),
    (r"破\(Break\)",                "break"),
    (r"害\(Harm\)",                 "harm"),
    (r"刑\(Punishment\)",           "punishment"),
    (r"鬼門\(GhostGate\)",          "ghost_gate"),
    (r"怨嗔",                       "resentment"),
]

POSITION_KO = {"년": "year", "월": "month", "일": "day", "시": "hour"}


def _strip_ansi(s):
    """Remove the unicode box-drawing and decorative chars for easier parsing."""
    return s


def parse_report(api_response):
    """Parse the existing API report text into a structured chart dict."""
    text = api_response["report"]
    lines = text.split("\n")

    chart = {
        "subject": {},
        "pillars": {},
        "day_master": {},
        "five_elements_count": {},
        "interactions": [],
        "sin_sal_present": [],
        "sin_sal_absent": [],
        "void_branches": {"branches": [], "present_in_chart": [], "void_pillars": []},
        "dae_un": [],
        "se_un": {},
    }

    # --- Subject info ---
    for line in lines:
        if line.startswith("Name:"):
            chart["subject"]["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("Gender:"):
            chart["subject"]["gender"] = "F" if "Female" in line else "M"
        elif line.startswith("Date of Birth:"):
            chart["subject"]["birth_date_str"] = line.split(":", 1)[1].strip()
        elif line.startswith("Birth Time:"):
            chart["subject"]["birth_time_str"] = line.split(":", 1)[1].strip()
        elif line.startswith("Analyzed:"):
            chart["subject"]["analyzed_at"] = line.split(":", 1)[1].strip()

    # --- Four Pillars block ---
    # Find the row with the jiazi pairs
    for i, line in enumerate(lines):
        if "Pillar" in line and "간지" in line:
            # Extract jiazi values
            # They appear as 4 two-char CJK chunks
            jiazi_matches = re.findall(r"[\u4e00-\u9fff]{2}", line)
            if len(jiazi_matches) >= 4:
                positions = ["year", "month", "day", "hour"]
                for pos, jiazi in zip(positions, jiazi_matches[:4]):
                    stem = jiazi[0]
                    branch = jiazi[1]
                    stem_id = STEM_CH_TO_ID.get(stem)
                    branch_id = BRANCH_CH_TO_ID.get(branch)
                    stem_elem, stem_yy = STEM_ELEM[stem_id]
                    branch_elem, zodiac, hidden = BRANCH_INFO[branch_id]
                    chart["pillars"][pos] = {
                        "position": pos,
                        "stem": stem, "branch": branch,
                        "jiazi": jiazi,
                        "stem_id": stem_id, "branch_id": branch_id,
                        "stem_element": stem_elem, "stem_yin_yang": stem_yy,
                        "branch_element": branch_elem, "zodiac": zodiac,
                        "hidden_stems": hidden,
                    }
            break

    # --- Ten Gods row (stem-level) ---
    in_ten_god_block = False
    for i, line in enumerate(lines):
        if "Ten God" in line and "십성" in line:
            # The Korean ten gods are in this same line
            ko_matches = re.findall(r"[\uac00-\ud7a3]{2}", line)
            # Filter to only the 4 ten god labels (after "십성")
            positions = ["year", "month", "day", "hour"]
            # The labels follow "십성" — collect them
            relevant = [k for k in ko_matches if k in TEN_GOD_KO_TO_ID and k != "십성"]
            if len(relevant) >= 4:
                for pos, label in zip(positions, relevant[:4]):
                    chart["pillars"][pos]["ten_god_stem_ko"] = label
                    chart["pillars"][pos]["ten_god_stem"] = TEN_GOD_KO_TO_ID[label]
            break

    # --- Branch Ten Gods (지지십성) ---
    for i, line in enumerate(lines):
        if "지지십성" in line:
            ko_matches = re.findall(r"[\uac00-\ud7a3]{2}", line)
            relevant = [k for k in ko_matches if k in TEN_GOD_KO_TO_ID and k != "지지십성"]
            if len(relevant) >= 4:
                positions = ["year", "month", "day", "hour"]
                for pos, label in zip(positions, relevant[:4]):
                    chart["pillars"][pos]["ten_god_branch_ko"] = label
                    chart["pillars"][pos]["ten_god_branch"] = TEN_GOD_KO_TO_ID[label]
            break

    # --- 12 Stage row ---
    for i, line in enumerate(lines):
        if "12 Stage" in line:
            ko_matches = re.findall(r"[\uac00-\ud7a3]+", line)
            stages = [k for k in ko_matches if k in STAGE_KO_TO_ID]
            if len(stages) >= 4:
                positions = ["year", "month", "day", "hour"]
                for pos, label in zip(positions, stages[:4]):
                    chart["pillars"][pos]["twelve_stage_ko"] = label
                    chart["pillars"][pos]["twelve_stage"] = STAGE_KO_TO_ID[label]
            break

    # --- Five Elements ---
    for line in lines:
        m = re.match(r"\s*Wood 목: (\d+)\s+Fire 화: (\d+)\s+Earth 토: (\d+)\s+Metal 금: (\d+)\s+Water 수: (\d+)", line)
        if m:
            chart["five_elements_count"] = {
                "wood": int(m.group(1)), "fire": int(m.group(2)),
                "earth": int(m.group(3)), "metal": int(m.group(4)),
                "water": int(m.group(5))
            }
            break

    # --- Day Master ---
    for line in lines:
        m = re.search(r"Day Master \(일간\): ([\u4e00-\u9fff]) — (\w+)", line)
        if m:
            day_stem = m.group(1)
            stem_id = STEM_CH_TO_ID[day_stem]
            elem, yy = STEM_ELEM[stem_id]
            chart["day_master"] = {
                "stem": day_stem, "stem_id": stem_id,
                "element": elem, "yin_yang": yy
            }
            break

    # --- Pillar Interactions ---
    interaction_section = False
    pos_pairs = {
        "월년": ("month", "year"), "시년": ("hour", "year"),
        "일월": ("day", "month"),   "시일": ("hour", "day"),
        "월일": ("month", "day"),   "년일": ("year", "day"),
        "년월": ("year", "month"),
    }
    for line in lines:
        if "PILLAR INTERACTIONS" in line:
            interaction_section = True
            continue
        if interaction_section and ("SPECIAL STARS" in line or "신살" in line and "神煞" in line):
            break
        if interaction_section:
            # Try to extract pair label and types
            pair_match = re.search(r"\(([가-힣]{2})\)", line)
            if pair_match and pair_match.group(1) in pos_pairs:
                a, b = pos_pairs[pair_match.group(1)]
                rest = line.split(":", 1)[-1] if ":" in line else line
                for pattern, itype in INTERACTION_PATTERNS:
                    m = re.search(pattern, rest)
                    if m:
                        entry = {"pillars": [a, b], "type": itype}
                        if itype == "combination" and m.groups():
                            result_raw = m.group(1).lower()
                            # Normalize API's element names to our convention
                            elem_map = {"tree": "wood", "wood": "wood", "fire": "fire",
                                        "earth": "earth", "metal": "metal", "water": "water"}
                            entry["result"] = elem_map.get(result_raw, result_raw)
                        chart["interactions"].append(entry)

    # --- Sin sal ---
    sin_section = False
    for line in lines:
        if "SPECIAL STARS" in line:
            sin_section = True
            continue
        if sin_section and "VOID BRANCHES" in line:
            break
        if sin_section:
            # Split on the arrow → to avoid nested-paren regex problems
            if "→" not in line:
                continue
            left, right = line.split("→", 1)
            loc = right.strip()
            # The left side has Chinese + Korean + parenthetical description
            # Extract first Korean cluster after the Chinese chars
            ko_match = re.search(r"([가-힣]+)\s*\(", left)
            if not ko_match:
                continue
            ko_label = ko_match.group(1).strip()
            sin_id = SIN_SAL_KO_TO_ID.get(ko_label, ko_label)
            if loc == "absent":
                chart["sin_sal_absent"].append(sin_id)
            else:
                loc_clean = loc.lower()
                if "month" in loc_clean: location = "month"
                elif "year" in loc_clean: location = "year"
                elif "day" in loc_clean and "master" not in loc_clean: location = "day"
                elif "hour" in loc_clean: location = "hour"
                elif "present" in loc_clean: location = "day_master"
                else: location = loc
                chart["sin_sal_present"].append({
                    "id": sin_id, "korean": ko_label, "location": location
                })

    # --- Void branches ---
    for i, line in enumerate(lines):
        if "Void branches" in line:
            m = re.search(r":\s*([\u4e00-\u9fff,\s]+)", line)
            if m:
                branches = [b.strip() for b in m.group(1).split(",") if b.strip()]
                chart["void_branches"]["branches"] = branches
        if "Affected pillars" in line:
            after_colon = line.split(":", 1)[-1].strip()
            if after_colon and after_colon != "none":
                # parse positions
                pillars = []
                for k, v in POSITION_KO.items():
                    if k in after_colon:
                        pillars.append(v)
                chart["void_branches"]["void_pillars"] = pillars

        # Determine which void branches are present in chart
    chart_branches = [chart["pillars"][p]["branch"] for p in ["year","month","day","hour"] if p in chart["pillars"]]
    chart["void_branches"]["present_in_chart"] = [b for b in chart["void_branches"]["branches"] if b in chart_branches]

    # --- Dae-un table ---
    dae_section = False
    for line in lines:
        if "MAJOR LUCK PERIODS" in line:
            dae_section = True
            continue
        if dae_section and "ANNUAL FORTUNE" in line:
            break
        if dae_section:
            m = re.match(r"\s*(\d+)(★?)\s+([\u4e00-\u9fff]{2})\s+(.+)", line)
            if m:
                age = int(m.group(1))
                is_void = m.group(2) == "★"
                jiazi = m.group(3)
                rest = m.group(4)
                # extract stem and branch ten gods (Korean labels)
                ko_labels = re.findall(r"[\uac00-\ud7a3]{2,3}", rest)
                stem_god = ko_labels[0] if len(ko_labels) > 0 else None
                branch_god = ko_labels[1] if len(ko_labels) > 1 else None
                stage = ko_labels[2] if len(ko_labels) > 2 else None
                spirit = ko_labels[3] if len(ko_labels) > 3 else None
                chart["dae_un"].append({
                    "age_start": age, "jiazi": jiazi, "is_void": is_void,
                    "stem_ten_god_ko": stem_god, "branch_ten_god_ko": branch_god,
                    "twelve_stage_ko": stage, "spirit_ko": spirit,
                    "stem_ten_god": TEN_GOD_KO_TO_ID.get(stem_god) if stem_god else None,
                    "branch_ten_god": TEN_GOD_KO_TO_ID.get(branch_god) if branch_god else None,
                })

    # --- Se-un table (annual) ---
    se_section = False
    se_entries = []
    for line in lines:
        if "ANNUAL FORTUNE" in line:
            se_section = True
            continue
        if se_section and "MONTHLY FORTUNE" in line:
            break
        if se_section:
            is_current = "▶" in line
            m = re.match(r"\s*[▶]?\s*(\d{4})\s+([\u4e00-\u9fff]{2})\s+(.+)", line)
            if m:
                year = int(m.group(1))
                jiazi = m.group(2)
                ko_labels = re.findall(r"[\uac00-\ud7a3]{2,3}", m.group(3))
                stem_god = ko_labels[0] if len(ko_labels) > 0 else None
                entry = {
                    "year": year, "jiazi": jiazi, "is_current": is_current,
                    "stem_ten_god_ko": stem_god,
                    "stem_ten_god": TEN_GOD_KO_TO_ID.get(stem_god) if stem_god else None,
                }
                se_entries.append(entry)
    if se_entries:
        current = next((e for e in se_entries if e["is_current"]), None)
        chart["se_un"] = {
            "entries": se_entries,
            "current": current,
            "current_year": current["year"] if current else None
        }

    return chart


if __name__ == "__main__":
    import json, urllib.request
    # Demo
    req = urllib.request.Request(
        "https://saju-api-eight.vercel.app/api/saju",
        data=json.dumps({"year":1990,"month":5,"day":15,"hour":14,"minute":30,"gender":"F","name":"Test"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        api_response = json.loads(r.read())
    chart = parse_report(api_response)
    print(json.dumps(chart, ensure_ascii=False, indent=2))
