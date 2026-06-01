# I Ching and Saju reference library

A consistently indexed, public-domain-friendly reference for I Ching divination and Korean Saju (Four Pillars of Destiny) readings. Built for clean ingestion by code or master prompts.

## What's here

```
divination/
├── index.json                       # master index, all entries with stable schemas
├── sources.md                       # PD source provenance + ctext.org / Wikisource links
├── iching/
│   ├── hexagrams/                   # 64 markdown files, one per hexagram
│   └── trigrams/                    # 8 markdown files, one per trigram
└── saju/
    ├── stems/                       # 10 heavenly stems (천간)
    ├── branches/                    # 12 earthly branches (지지)
    ├── ten_gods/                    # 10 sip-sin relationships
    ├── sin_sal/                     # 30 sin sal stars (10 base + 20 extended)
    ├── relationships/               # 9 relationship matrices
    │   ├── stem_combinations.md     # 천간합 (5 pairs)
    │   ├── stem_clashes.md          # 천간충 (4 pairs)
    │   ├── branch_six_combinations.md  # 지지육합 (6 pairs)
    │   ├── branch_three_harmonies.md   # 삼합 (4 trinities)
    │   ├── branch_seasonal_meetings.md # 방합 (4 trinities)
    │   ├── branch_six_clashes.md    # 육충 (6 pairs)
    │   ├── branch_six_harms.md      # 육해 (6 pairs)
    │   ├── branch_six_breaks.md     # 육파 (6 pairs)
    │   └── branch_punishments.md    # 형 (4 types)
    ├── pillars/                     # 60 individual pillar interpretations
    ├── elements.md                  # five elements (오행) + relationships
    ├── twelve_stages.md             # 12 life stages (십이운성)
    ├── twelve_stages_lookup.md      # full 10 × 12 stage lookup matrix
    ├── sixty_jiazi.md               # 60-pillar cycle (now with nayin + 공망)
    ├── nayin.md                     # 30 nayin sound elements
    ├── empty_branches.md            # 공망 lookup by 旬
    ├── solar_terms.md               # 24 solar terms (이십사절기)
    ├── yong_sin.md                  # useful god (용신) selection primer
    ├── patterns.md                  # pattern theory (격국) primer
    ├── dae_un.md                    # 10-year luck cycle (대운) rules
    └── geunmyo.md                   # pillar life-stage framework (근묘화실)
```

## What got added in schema 1.1

- **Relationship matrices** — all the combinations, clashes, harmonies, punishments. Without these, the data is just a glossary.
- **Pillar interpretations** — 60 individual files, one per jiazi, with stem-on-branch analysis, twelve-stage position, nayin, and empty branches.
- **Twelve stages lookup** — the full 10 stems × 12 branches matrix.
- **Nayin** — 30 sound elements covering the 60 jiazi.
- **Empty branches (공망)** — lookup by 旬.
- **20 additional sin sal** — totalling 30.
- **Four primers** — 용신, 격국, 대운, 근묘화실 — the reading methodology.
- **sources.md** — direct links to ctext.org / Wikisource for the classical Chinese originals.


## Schema

Every markdown file uses YAML frontmatter so it can be parsed without touching the prose body. The `type` field tells you what schema to expect.

### Hexagram
```yaml
type: hexagram
id: 1                          # King Wen number, 1–64
slug: 01-qian-qian             # filename slug
king_wen: 1
name_zh: 乾
name_pinyin: Qián
name_en: "The Creative / Force"
name_ko: 중천건
name_ko_hanja: 重天乾
trigram_lower: qian            # stable id, see trigrams/
trigram_upper: qian
trigram_lower_zh: 乾
trigram_upper_zh: 乾
binary_bottom_to_top: "111111" # 6 chars, bottom line first
element_lower: metal
element_upper: metal
keywords: [creative, heaven, strength, initiating, "pure yang"]
```

### Trigram
```yaml
type: trigram
id: qian                       # stable id used as foreign key in hexagrams
binary_bottom_to_top: "111"
name_zh: 乾
name_pinyin: Qián
name_ko: 건
name_ko_hanja: 乾
name_en: Heaven
element: metal
attribute: "creative, strong"
family: father
body: head
animal: horse
direction_pre_heaven: south
direction_post_heaven: northwest
season: "late autumn"
color: "deep red / white"
keywords: [...]
```

### Heavenly stem
```yaml
type: heavenly_stem
id: 1                          # 1–10
chinese: 甲
korean: 갑
korean_romanized: gap
pinyin: jiǎ
element: wood
yin_yang: yang
sequence: 1
keywords: [...]
```

### Earthly branch
```yaml
type: earthly_branch
id: 1                          # 1–12
chinese: 子
korean: 자
korean_romanized: ja
pinyin: zǐ
element: water
yin_yang_polar: yang           # positional polarity
yin_yang_operational: yin      # used when figuring Ten Gods
zodiac: rat
hour: "23:00–01:00"
lunar_month: 11
solar_month: "winter solstice"
season: winter
direction: north
hidden_stems: [癸]
keywords: [...]
```

### Ten God
```yaml
type: ten_god
id: bi_jian                    # stable id
chinese: 比肩
korean: 비견
korean_romanized: bi-gyeon
relation_to_day_master: "same element, same polarity as Day Master"
category: "self / peers"
keywords: [...]
```

### Element, Life Stage, Solar Term, Sin Sal
Same pattern. See `index.json` for the canonical list of fields per type.

## Programmatic access

The fastest path is `index.json`:

```python
import json
idx = json.load(open("divination/index.json"))
qian = [h for h in idx["iching"]["hexagrams"] if h["id"] == 1][0]
```

For a full hexagram including judgment, image, interpretation, and changing-line notes, read the markdown file:

```python
import yaml, pathlib
raw = pathlib.Path("divination/iching/hexagrams/01-qian-qian.md").read_text()
fm_str, body = raw.split("---\n", 2)[1:]  # split off frontmatter
fm = yaml.safe_load(fm_str)
```

## Lookups you can do directly from `index.json`

- hexagram by King Wen number → `iching.hexagrams[id-1]`
- hexagram by binary string → filter `iching.hexagrams` by `binary_bottom_to_top`
- trigram pair → upper/lower trigram ids
- stem/branch by Chinese, Korean, or id
- the 60 Jiazi → `saju.sixty_jiazi` (pre-built)
- which solar term currently active → `saju.solar_terms` (with Gregorian date hints)

## Sources and provenance

- I Ching judgments, images, and line notes — original synthesis informed by the James Legge translation (1882, public domain) and traditional Chinese commentaries that are themselves ancient and unencumbered.
- Saju structural data (stems, branches, elements, Ten Gods, Twelve Stages, Sin Sal) — traditional classical material with no modern copyright.
- All interpretive prose in this library is original synthesis and may be reused freely.

No Wilhelm/Baynes text is reproduced. No modern translator's prose is copied.

## Conventions

- Binary strings for trigrams and hexagrams are written bottom-to-top, matching how they are read in traditional commentary. Bit 0 = bottom line.
- Korean romanization uses the Revised Romanization of Korean.
- Pinyin uses tone marks.
- Saju months follow solar terms (the year starts at 입춘 / Lichun, around Feb 4), not the lunar new month.

## Extending

Run `python generate.py` from `build/` to rebuild the whole library from the data dicts at the top of the script. To add per-line full texts, alternative translations, or additional Sin Sal, expand the dicts and rerun.
