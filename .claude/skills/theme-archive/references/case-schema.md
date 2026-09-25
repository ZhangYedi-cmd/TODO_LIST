# case JSON schema

One file per case: `<archive>/cases/<id>.json`. `build_archive.py` renders it into the page; `validate_case.py` enforces the rules below. Rich-text fields accept only `<strong> <b> <br> <em>` (`**bold**` is converted to `<strong>`). The renderer adds fixed prefixes, so **do not** type them yourself: `gene` → `🧬 题材基因：`, `confirm` → `✔ 确认：`, `risk` → `⚠️ `, timeline `why` → `为什么：`, `ringSummary` and scenario `branch` → `▸ `.

| field | type | rendered as | rule |
|---|---|---|---|
| `schemaVersion` | 1 | — | |
| `id` | kebab-case ascii | URL hash `#id`, related-case tags | unique, stable, e.g. `tio2-price-hike-7` |
| `date` | `YYYY-MM-DD` | card date, header clock | report date (CST) |
| `title` | text ≤ 20 | card title, `<h1>`, footer | event + the hard number (`光芯片缺口扩至30%+`) |
| `subtitle` | text 60–110 | `.csub`, `.sub` | 3–4 hardest numbers joined by ` · ` |
| `grade.tone` | `fire`/`bolt`/`warn` | badge colour, index stats | see methodology §2 |
| `grade.text` | text | first badge, card `.crate` | `<emoji> <定性> · <矛盾点>`, emoji matches tone |
| `driver` | 产业周期/地缘冲突/政策驱动/证伪型/映射型 | badge, card | |
| `pricing` | 未定价/部分定价/已定价 | badge, card chip, index filter | exact values only |
| `mainline` | text | badge, card chip, related-case grouping | reuse existing names |
| `archiveLevel` | 正式档/降档 | card `data-grade`, ⚑ chip, gradedown badge | |
| `downgradeBadge` | text | gradedown badge | only for 降档; default `⚑ 降档入库 · 只配情绪波段，不格局中线` |
| `relatedCases` | [id] | `主线联动档案` tags | optional cross-mainline links; same-mainline cases are added at build time |
| `positionNote` | text 55–85 | `.posnote`, card `.cpos` | one-line: hardest fact + pricing verdict |
| `pricingDetail` | rich 300–800 | collapsible `定价状态详版` | 催化时点 → 盘面状态 → 结论 |
| `facts[]` | `{key, value(rich), warn}` ×6–8 | 核心事实 grid | one `warn:true` 争议点; last = 盘面验证 |
| `timeline[]` | `{when, what(rich), why(rich)}` | 主线更新 | append for follow-ups |
| `verdict` | rich 500–700 | 逻辑推演 | 三个要害 / ①②③ + 隐藏面 |
| `rings[]` | `{name, verdict, points[2]}` ×4 | 产业链逻辑链条 | names exactly 变化/影响/业绩/股价 |
| `ringSummary` | rich 40–70 | `▸` line | 变化X、影响Y、业绩Z、股价W——结论 |
| `assessment[]` | rich ×3 | list under rings | [0] starts `闭合度 <strong>NN%</strong>`, [1] 边界, [2] 主线联动 |
| `stockTiers[]` | `{title, driver, stocks[]}` | stock tiers | order 🔥主攻 > 🏛️容量中军 > 🧬观察 > ⚡情绪小票 > 👑情绪龙 |
| stock | `{name, code, tag, cap, logic, detail, gene?, risk}` | card | `cap` may be `""` (filled from quotes at build); `gene` required for ⚡/👑 |
| `history[]` | rich ×3–4 | 📜 历史妖股记忆 / 同类行情参照 | year + event + numbers + lesson |
| `coreLinks[]` | `{name, code, tag, logic, detail, confirm, risk}` ×2–3 | ⛓️ 核心环节 | logic = `产业地位 \| 弹性来源 \| 约束条件` |
| `extendedLinks[]` | `{name, code, tag, logic, detail, risk}` ×1–3 | 🔗 延伸环节 | |
| `notInChain[]` | `{name, code:"—", logic}` ×2–4 | 🚫 不在传导链上 | companies, wrong templates, cost-hurt parties |
| `decisionChain[]` | `{name, text(rich), style}` ×8 | 合规决策链 | names fixed; 07 text fixed; style `dim` for 仓位, `alert` for 特别提醒 |
| `scenarios[]` | `{branch, trigger, state, signal}` ×3–4 | 情景推演 | mutually exclusive, base case first |
| `signals` | `{verify[4–5], falsify[4–5]}` | 信号对照台 | measurable, time-bound |
| `calendar[]` | `{when, what, why}` ×3–5 | 跟踪日历 | |
| `sources` | text | 数据来源 | `来源（时间） ｜ 来源（时间）` |
| `legacy` | bool | — | set by `import_html.py`; relaxes validation for imported cases |

Computed at build time (never write them): index stats, the `标的 N` chip (= stock-tier cards), the five names on the index card (stock tiers then core links), `覆盖标的` (= all cards except 🚫), search strings, the `（N 字）` count, same-mainline related cases, and every stock card's `cap` when a quotes file is passed.

## Minimal example (shape only — real cases are much denser)

```json
{
  "schemaVersion": 1,
  "id": "example-price-hike",
  "date": "2026-09-24",
  "title": "某材料第三轮集体调价",
  "subtitle": "龙头 9/23 盘后发函 · 国内 +800 元/吨 · 年内第三轮 · 行业开工率 68%",
  "grade": {"tone": "bolt", "text": "⚡ 涨价实锤级 · 函已发三轮、链内龙头零反应"},
  "driver": "产业周期",
  "pricing": "未定价",
  "mainline": "化工涨价链",
  "archiveLevel": "正式档",
  "relatedCases": [],
  "positionNote": "……（55–85 字）",
  "pricingDetail": "催化由<strong>财联社 9/23 17:40</strong> 发出，属盘后落地……",
  "facts": [{"key": "核心事实", "value": "……", "warn": false}, {"key": "争议点：函价 ≠ 成交价", "value": "……", "warn": true}, {"key": "盘面验证", "value": "……", "warn": false}],
  "timeline": [{"when": "2026-09-23 17:40", "what": "……", "why": "本档建档时点"}],
  "verdict": "这是「涨价实锤级」催化，<strong>三个要害</strong>：一是……",
  "rings": [{"name": "变化", "verdict": "实", "points": ["……", "……"]}, {"name": "影响", "verdict": "强", "points": ["……", "……"]}, {"name": "业绩", "verdict": "存疑", "points": ["……", "……"]}, {"name": "股价", "verdict": "未动", "points": ["……", "……"]}],
  "ringSummary": "变化实、影响强、业绩存疑、股价未动——……",
  "assessment": ["闭合度 <strong>60%</strong>：……", "边界：……", "主线联动：……"],
  "stockTiers": [{"title": "🔥 主攻·资源映射", "driver": "产业周期", "stocks": [{"name": "某公司", "code": "600000", "tag": "……", "cap": "", "logic": "……", "detail": "……", "risk": "……"}]}],
  "history": ["……", "……", "……"],
  "coreLinks": [{"name": "某公司", "code": "600000", "tag": "……", "logic": "…… | …… | ……", "detail": "……", "confirm": "…… / ……", "risk": "……"}],
  "extendedLinks": [],
  "notInChain": [{"name": "……", "code": "—", "logic": "……"}, {"name": "……", "code": "—", "logic": "……"}],
  "decisionChain": [{"name": "定性", "text": "……", "style": ""}, {"name": "主攻优先级", "text": "……", "style": ""}, {"name": "情绪优先级", "text": "……", "style": ""}, {"name": "确认条件", "text": "……", "style": ""}, {"name": "验证点", "text": "……", "style": ""}, {"name": "证伪点", "text": "……", "style": ""}, {"name": "仓位", "text": "交易者自管，本图不涉及。", "style": "dim"}, {"name": "特别提醒", "text": "……", "style": "alert"}],
  "scenarios": [{"branch": "……（基准情形）", "trigger": "……", "state": "……", "signal": "……"}],
  "signals": {"verify": ["……"], "falsify": ["……"]},
  "calendar": [{"when": "10 月下旬", "what": "……", "why": "……"}],
  "sources": "财联社（9/23 17:40） ｜ 公司公告（9/23） ｜ 东财行情（9/24）"
}
```
