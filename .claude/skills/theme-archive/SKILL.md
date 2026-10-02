---
name: theme-archive
description: Produce the daily 题材档案库 (A股题材研究档案) report — collect the day's catalysts and A-share market data, analyse each catalyst with the archive's framework (入库四判据, 定价状态 with excess returns, 产业链四环与闭合度, 主攻/情绪/观察 stock tiers, 八要素合规决策链, 情景推演, 信号对照台, 跟踪日历), write new cases or 主线更新 as JSON, and build the single-file HTML archive whose style matches the reference archive exactly. Use for the weekday scheduled run, or when asked for 题材档案/题材日报/今日题材/复盘档案, to add or update a case, or to rebuild the archive page.
---

# 题材档案库 · 每日报告

Each trading day this skill turns the day's catalysts into 1–4 archive cases (plus follow-ups on existing 主线) and rebuilds `dist/题材档案库.html`, a self-contained page identical in markup and CSS to the reference archive (the renderer reproduces the reference byte for byte from its JSON).

- Scripts: `.claude/skills/theme-archive/scripts/` — Python 3.9+, stdlib only. Below, `S=.claude/skills/theme-archive/scripts`.
- Archive home: `$THEME_ARCHIVE_HOME`, default `<repo>/theme-archive/` → `cases/*.json` (one per case), `data/YYYYMMDD/` (collected data), `dist/` (HTML).
- Read before writing the first case of a session: `references/methodology.md` (the analysis rules), `references/case-schema.md` (fields), and the two newest cases in `cases/` as style exemplars.

## Workflow

Run after 15:30 CST (A-share close); 17:30–19:00 catches most post-close news. Dates are CST.

### 1. Prepare: calendar, data, candidates

```bash
S=.claude/skills/theme-archive/scripts
python3 $S/daily.py prepare            # add --date YYYY-MM-DD for another day
```

- Exit **3** = not a trading day. On a scheduled run, stop and report "休市，无报告". Only continue with `--force` if a person asked for a holiday/weekend report (market data then refers to the last trading day, as the reference archive does for weekend cases).
- Exit **2** = data hosts blocked (typical in sandboxed cloud environments). Continue in **fallback mode**: collect catalysts and 盘面 numbers with the WebSearch tool (query list in `references/data-sources.md`), and name the host(s) to allow in your final message.
- Output: `data/YYYYMMDD/market.json` (indices, breadth, 涨停/跌停/炸板, 涨停题材地图, board ranks), `quotes.json` (all A-shares), `news.json`, `reports.json`, `candidates.md`.

`python3 $S/daily.py status` lists existing cases by 主线 with their last update.

### 2. Pick the day's events

Read `candidates.md` (or, in fallback mode, run 5–8 searches such as `9月24日 盘后 涨价`, `9月24日 创历史新高`, `9月24日 涨停复盘 题材`, `财联社 9月24日 停产`). For each candidate apply methodology §1:

1. Check the four admission criteria: 精确数字 / 预期差 / 可证伪胜负手 / A 股可映射. All four → 正式档. ①③ only → 降档. ① missing → skip.
2. Does it continue an existing case (same 主线, same variable) or fire one of its 验证/证伪 signals? → **主线更新** (step 4b), not a new case. Updates are cheap and do not count toward the new-case quota: do every one that the day's news triggers.
3. Choose 2–4 new cases, favouring hard supply/price variables and post-close news. One solid case beats three thin ones.

### 3. Research each new case

Work in this order and keep every number with its source and time:

1. **Facts** (WebSearch, 4–8 queries): primary source and exact timestamps (首发 / 扩散), the numbers, previous rounds, supply–demand context, and the strongest counter-argument (争议点).
2. **Chain & stocks**: map 上游/中游/下游 and who is hurt. Candidate stocks come from the news stock lists, `market.json` concept boards and 涨停题材地图, and your knowledge. Verify main-business relevance before using a name.
3. **Market evidence**: `python3 $S/stock_lookup.py 名称或代码 ... --date YYYY-MM-DD` prints close, pct, 超额 vs 上证, 成交, 换手, the multi-day path, and ready-made `cap` / 盘面 strings (cached for the build). When the iFinD MCP tools are connected (`references/data-sources.md`), take numbers the collectors could not fetch from them and record each stock with `--manual … --source "iFinD M/D"`. Otherwise, in fallback mode, search `<名称> 9月24日 收盘 涨跌幅 成交额`, cross-check important numbers in two sources (search summaries often garble units: MW vs 万千瓦, billion vs 亿), then record each verified stock with `python3 $S/stock_lookup.py --manual CODE 名称 --pct X --price P [--float-cap 亿] [--amount 亿] [--turnover %] --index-pct <上证 pct> --source "来源 M/D" --date YYYY-MM-DD` — it computes 超额 and the `cap` line, and the build and validator then use these numbers like fetched data.
4. **Judge**: 定价状态 (methodology §3), grade/driver (§2), ring verdicts and 闭合度 (§7), tiers (§8).
5. **History**: 3–4 past analogs with year, numbers and the lesson.

### 4a. Write a new case

```bash
python3 $S/new_case.py <kebab-id> --title "标题" --mainline "已有主线名" --driver 产业周期 --date YYYY-MM-DD [--downgrade]
```

`--downgrade` scaffolds a 降档 case (⚠ 题材催化级, the ⚑ badge, and a「（本档无合格主攻标的）」核心环节 card to keep or delete).

Then replace every `TODO` in `cases/<id>.json`. Write the body first (facts → timeline → verdict → rings/assessment → tiers → decision chain → scenarios → signals → calendar → pricingDetail), then the headline fields (positionNote, subtitle, grade, title) so they summarize it. Leave `cap` as `""`: the build fills it for every stock in `lookup.json` or `quotes.json` (in fallback mode, record the stock with `stock_lookup.py --manual` first; without a float cap the line reads `价格 元 · M/D ±x.xx%`). Match the reference density: fact cards 150–250 字, core-link details 200–300 字, verdict 500–700 字.

### 4b. 主线更新 (follow-up on an existing case)

Keep the case's original `date`. Then:

- **Timeline**: add one entry per new event: `when` = `YYYY-MM-DD HH:MM` when the time is known, else `YYYY-MM-DD 盘后` / `晚` / `盘前`; `what`; `why` = its role (二段催化 / 验证信号 / 证伪信号 / 盘后扩散未定价). Keep the list chronological: when an undated row such as `待定` resolves, replace it with the dated entry (say in `why` which watch item it resolves); otherwise insert new entries before any remaining undated rows.
- **Facts**: keep the original 盘面验证 card but rename it `盘面验证 · M/D 建档`, and add `盘面验证 · M/D` for the new session. Add or adjust other cards only when a fact changed.
- **Re-judge**: `pricing`, `grade`, ring verdicts and points, `ringSummary`, `assessment[0]` (write `闭合度 NN%（M/D 主线更新，建档时 XX%）`) and `assessment[2]`, `positionNote`, `pricingDetail` (append the new 催化时点/盘面), and a paragraph at the end of `verdict`.
- **Forward-looking parts go stale fastest**: redo decision steps 04/05/06/08; re-base `scenarios` if the base case's premise is now false; in `signals` and `calendar`, *replace* items that have resolved (they now live in the timeline) so the lists stay at 4–6 and 3–5.
- Convert any legacy `**bold**` you touch to `<strong>`.

### 5. Validate and build

```bash
python3 $S/daily.py finish --date YYYY-MM-DD
```

This validates every case dated or updated that day (schema, fixed structure, enums, compliance wording, numbers vs market data), then renders all cases to `dist/题材档案库.html` (plus a dated copy). It refreshes every stock card's quote line from the newest market data and links cases on the same 主线. Fix all ERRORs and re-run. Treat WARNs about lengths and counts as style drift and fix them unless there is a reason not to.

### 6. Deliver

- Report the output path, then one line per new case (`id · grade · 定价状态 · 一句话定位`) and per 主线更新, plus data gaps (blocked hosts, fallback numbers).
- If the run's instructions say where to publish (commit and push the `theme-archive/` changes to a given branch, attach the HTML, or update an artifact), do that. If the archive lives in git, commit the new/changed `cases/*.json`, the day's `data/YYYYMMDD/{market,news,candidates}` files and `dist/`.
- Scheduled runs have no one to answer questions: make the calls yourself, following methodology.md, and note judgement calls in the summary.

## Rules that must hold

- **Compliance**: no prices to buy or sell at, no position sizing, no buy/sell wording. Step 07 is always `交易者自管，本图不涉及。`. Broker ratings or targets may only be quoted as facts, with the firm and date.
- **No invented numbers.** Every figure must come from collected data or a source you read. If a number cannot be found, state the fact qualitatively.
- **Never hand-edit the HTML.** Change the JSON and rebuild. The CSS and router live in `assets/` and are copied verbatim from the reference archive.
- Enum values are exact: `pricing` ∈ 未定价/部分定价/已定价, `driver` ∈ 产业周期/地缘冲突/政策驱动/证伪型/映射型, `grade.tone` ∈ fire/bolt/warn.

## Maintenance

- **Seed or migrate an archive**: `python3 $S/import_html.py existing.html` writes one JSON per case. `python3 $S/selftest.py --reference existing.html` proves the rebuild is byte-identical.
- **Where the archive lives**: the default `<repo>/theme-archive/` is git-ignored (this repo is public). Point `THEME_ARCHIVE_HOME` at a private location, or remove the `/theme-archive/` line from `.gitignore` to version the archive in this repo.
- **Trading calendar**: add next year's exchange holidays to `EXCHANGE_HOLIDAYS` in `scripts/ta_common.py` when SSE publishes them (late December). `prepare` warns when the year is missing.
- **Paid data**: the iFinD MCP servers are registered in the repo's `.mcp.json` (token from `IFIND_MCP_TOKEN`, host `api-mcp.51ifind.com:8643`). `python3 $S/mcp_client.py probe` checks them. Wind/Tushare output can be written into the same `quotes.json` / `market.json` shapes (see `references/data-sources.md`).
- `python3 $S/selftest.py` runs the offline test suite.
