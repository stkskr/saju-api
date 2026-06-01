# Proposed API response schema (v2)

Your current API returns a single `report` field with a pretty-printed text block. That's great for direct human reading but suboptimal for piping into an LLM reading pipeline — the LLM has to parse text to extract values, which is fragile.

**Recommendation:** keep `report` (for human consumption), add a `chart` field with structured data.

## Proposed response

```json
{
  "report": "...current ASCII report...",
  "chart": {
    "subject": {
      "name": "Test",
      "gender": "F",
      "birth": {
        "year": 1990, "month": 5, "day": 15,
        "hour": 14, "minute": 30,
        "calendar": "solar"
      },
      "analyzed_at": "2026-06-01"
    },
    "pillars": {
      "year":  {"position": "year",  "stem": "庚", "branch": "午", "jiazi": "庚午", "jiazi_id": 7,
                "stem_ko": "경", "branch_ko": "오",
                "stem_element": "metal", "stem_yin_yang": "yang",
                "branch_element": "fire", "zodiac": "horse",
                "hidden_stems": ["丁", "己"],
                "ten_god_stem": "pyeon_in",   "ten_god_stem_ko": "편인",
                "ten_god_branch": "jeong_gwan", "ten_god_branch_ko": "정관",
                "twelve_stage": "tae",         "twelve_stage_ko": "태",
                "twelve_spirit": "jang_seong"},
      "month": {...same shape...},
      "day":   {...same shape...},
      "hour":  {...same shape...}
    },
    "day_master": {
      "stem": "壬", "element": "water", "yin_yang": "yang",
      "strength_assessment": "weak",
      "strength_factors": {
        "deuk_ryeong": false,
        "deuk_ji": false,
        "deuk_se": false
      }
    },
    "five_elements_count": {
      "wood": 0, "fire": 3, "earth": 2, "metal": 2, "water": 1
    },
    "interactions": [
      {"pillars": ["month", "year"], "type": "combination", "result": "fire"},
      {"pillars": ["hour", "year"],  "type": "combination", "result": "fire"},
      {"pillars": ["day", "month"],  "type": "ghost_gate"},
      {"pillars": ["hour", "day"],   "type": "combination", "result": "wood"},
      {"pillars": ["hour", "day"],   "type": "break"}
    ],
    "sin_sal_present": [
      {"id": "cheon_eul_gwi_in", "korean": "천을귀인", "location": "month"},
      {"id": "cheon_deok_gwi_in", "korean": "천덕귀인", "location": "hour"},
      {"id": "goe_gang_sal", "korean": "괴강", "location": "day_master"}
    ],
    "sin_sal_absent": ["wol_deok_gwi_in", "mun_chang_gwi_in", "yang_in", "do_hwa", "geum_yeo", "baek_ho", "hong_yeom"],
    "void_branches": {
      "branches": ["辰", "戌"],
      "present_in_chart": ["戌"],
      "void_pillars": ["day"]
    },
    "yong_sin": {
      "primary_strategy": "bu_eok",
      "primary_element": "water",
      "rationale": "Day Master 壬 (water) is weak — born in 巳 (fire month, 7-stage Void position). Needs water (peers) and metal (resource) for support."
    },
    "pattern": {
      "id": "jeong_jae_gyeok",
      "korean": "정재격",
      "english": "Direct Wealth pattern",
      "intact": true,
      "notes": "Month stem 辛 is Direct Resource, hour pillar 丁未 is Direct Wealth. Wealth pattern intact."
    },
    "dae_un": [
      {"age_start": 3, "jiazi": "庚辰", "stem_ten_god": "pyeon_in", "branch_ten_god": "pyeon_gwan",
       "twelve_stage": "myo", "spirit": "wol_sal", "is_void": true},
      ...10 entries total...
    ],
    "se_un": {
      "current_year": 2026,
      "current": {"jiazi": "丙午", "stem_ten_god": "pyeon_jae", ...},
      "upcoming": [...]
    }
  }
}
```

## Why each field matters

- **`pillars.{position}.jiazi_id`** — direct lookup key into `saju.pillars` in `index.json`
- **`pillars.{position}.ten_god_*`** — using the **id** form (`pyeon_in`) not just Korean lets the prompt builder pull the right file from `ten_gods/`
- **`interactions[].type`** — using **id strings** (`combination`, `clash`, `ghost_gate`, `break`) maps cleanly to relationship files
- **`sin_sal_present[]`** with **id** — direct lookup into `sin_sal/` files
- **`day_master.strength_assessment`** — pre-computed; the LLM doesn't need to figure it out from raw data
- **`yong_sin`** — pre-computed by your code (which knows the algorithm better than the LLM); the LLM uses it as a starting point
- **`pattern`** — same reasoning; computational, not interpretive

## What the LLM should NOT compute

If you can compute it deterministically, your code should. The LLM is for **interpretation**, not arithmetic. So:

- ✅ LLM job: "Given this 壬 day master is weak and 용신 is water, what does this mean for career?"
- ❌ Not LLM job: "Count the elements and decide if the day master is strong"

This makes readings **dramatically more reliable**.

## Optional but valuable additions

- **`compatibility_inputs`** — if reading is for a relationship match, accept a second chart
- **`focus`** field in the request — `"life" | "career" | "relationships" | "wealth" | "year"` — lets the prompt builder weight different reference files
- **`calendar`** field in request — `"solar" | "lunar"` so users can input either; defaulting solar
- **Locale handling** — `tz` field for non-Korea-time births (currently appears to assume Korea time?)
