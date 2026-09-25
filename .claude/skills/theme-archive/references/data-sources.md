# Data sources

The collectors use public web endpoints (no API key). Each source is optional: its outcome is written to the `status` block of the output file, and the workflow falls back to web search for anything missing.

## Hosts to allow

A cloud environment with restricted egress blocks every one of these; allow them (environment settings → Network access → allowed domains, or a broader access level), or run the skill from a machine with normal internet:

| host | used by | what |
|---|---|---|
| `push2.eastmoney.com` | collect_market, stock_lookup | index quotes, all A-share quotes (`clist`), board ranks, single-stock float shares |
| `push2his.eastmoney.com` | collect_market, stock_lookup | daily K-lines (trading-date check, multi-day paths, past-date closes) |
| `push2ex.eastmoney.com` | collect_market | 涨停 / 跌停 / 炸板 pools by date |
| `searchapi.eastmoney.com` | stock_lookup | name → code |
| `np-listapi.eastmoney.com`, `np-weblist.eastmoney.com` | collect_news | 东方财富 7x24 快讯 |
| `reportapi.eastmoney.com` | collect_news | 东财研报中心 (stock + industry reports, ratings) |
| `www.cls.cn` | collect_news | 财联社电报 |
| `zhibo.sina.com.cn` | collect_news | 新浪 7x24 |
| `www.cninfo.com.cn` | collect_news | 巨潮资讯 announcements (keyword-filtered) |
| `data.10jqka.com.cn` | collect_market | 同花顺涨停原因 (for the 涨停题材地图) |

## What each output holds

- `data/YYYYMMDD/market.json`: `report_date`, `trade_date` (last trading day ≤ report date), `indices` (上证/深成/创业板/科创50/沪深300/北证50: close, pct, amount), `breadth` (up/down/flat, total amount 亿), `limit_up` (code, name, pct, boards 连板, first/last seal time, seal fund, broken times, industry, 10jqka reason), `limit_down`, `broken`, `limit_up_count`, `theme_map` (涨停题材地图: theme → stocks), `concept_boards` / `industry_boards` (top/bottom 30 with leaders), `status`.
- `data/YYYYMMDD/quotes.json`: every A-share → price, pct, volume, amount, amplitude, turnover, PE(dyn/TTM), PB, vol ratio, high/low/open/prev close, total/float cap, 60-day & YTD pct, main net inflow, industry. Only written when the live snapshot really is the trade date's close (after 15:05 CST on a trading day, or any time before the next session).
- `data/YYYYMMDD/news.json`: flashes and announcements in the window *previous trading day 15:00 → report date 23:59*, each with `session` (盘前/盘中/午间/盘后/夜间/非交易日), deduplicated across sources (`also` lists the other sources).
- `data/YYYYMMDD/reports.json`: broker reports published that day (title, org, stock, rating, industry).
- `data/YYYYMMDD/lookup.json`: every stock you looked up with `stock_lookup.py` (close, pct, excess, amount, turnover, float cap, path, ready-made `cap` and `phrase`).
- `data/YYYYMMDD/candidates.md`: the triage list from `screen_candidates.py`.

## Web-search fallback (when a host is blocked)

Use the WebSearch tool and record the source + time in `sources`. Useful queries (replace dates):

- 当日复盘: `9月24日 A股 收评 涨停 题材`, `9月24日 涨停复盘 连板`, `9月24日 沪指 收盘 成交额`
- 催化: `9月24日 盘后 公告 涨价`, `财联社 9月24日 电报 涨价`, `9月24日 创历史新高 价格`, `9月24日 停产 减产`, `9月24日 发改委 工信部 通知`
- 个股: `<名称> 9月24日 收盘 涨跌幅 成交额`, `<名称> 2026 半年报 营收 毛利率`, `<名称> 互动平台 产能`
- 商品/行业: `<品种> 价格 9月24日 生意社`, `<品种> 期货 收盘 9月24日`, `SMM <品种> 报价`

When market numbers come from search snippets rather than the collectors:

- Cross-check each stock's move, and any number that carries the argument, in two sources. Search summaries sometimes garble units or translate them (1690 MW for 1690 万千瓦, "58.00 billion" for 58.00 亿); re-read the unit against the underlying fact.
- Record every verified stock with `stock_lookup.py --manual CODE 名称 --pct … --price … --index-pct … --source …` so the build fills its quote line and the validator can check the text against it.
- Write the data source as `Web 检索（9/24）` (or the outlet and time) in `sources`.
- Never invent a number: if a figure cannot be found, write the qualitative fact without it and say so.

## Paid terminals

The reference archive used iFinD for 盘面 data. If you have iFinD / Wind / Tushare Pro, write their output into the same `quotes.json` / `market.json` shapes (see `collect_market.py` for field names) and every other script works unchanged.
