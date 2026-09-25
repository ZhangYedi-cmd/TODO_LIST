#!/usr/bin/env python3
"""Shortlist the day's catalyst candidates from news.json (step 2 of the workflow).

    python3 screen_candidates.py [--date YYYY-MM-DD] [--top 25]

Scores every news item against the archive's admission rules (精确数字 /
预期差 / 可证伪 / A股可映射), clusters near-duplicates, marks items that touch
an existing 主线 (candidates for a 主线更新 instead of a new case), and shows
how the mentioned stocks traded.  Output: data/YYYYMMDD/candidates.md (+ .json).
It is a triage aid: the final pick is an analyst judgement (see methodology.md).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import data_dir, load_cases, read_json, today_cn, write_json  # noqa: E402

NUM = re.compile(r"[+-]?\d+(?:\.\d+)?\s*(?:%|％|pct|个百分点|元/吨|美元/桶|美元/吨|美元|欧元|亿元?|万吨|万桶|吨|GW|MW|TWh|GWh|倍|片/月|家|台|颗|万片|万辆|bp|美分)")
KEYWORDS = {
    3: ("涨价", "提价", "调价", "挺价", "上调价格", "价格上调", "报价上调", "创历史新高", "创纪录", "历史新高", "史上首",
        "停产", "减产", "停运", "断供", "中断", "遇袭", "制裁", "禁令", "禁止出口", "反倾销", "EOL", "缺口", "短缺"),
    2: ("订单", "中标", "扩产", "量产", "突破", "首发", "发布", "政策", "通知", "意见", "方案", "发改委", "工信部",
        "商务部", "国务院", "药监局", "能源局", "新高", "紧缺", "供不应求", "交期", "排产", "库存", "开工率", "出口"),
    1: ("预计", "同比", "环比", "产能", "合同", "合作", "上线", "招标", "期货", "现货"),
}
NOISE = ("收评", "午评", "早评", "盘前必读", "开盘", "涨停复盘", "龙虎榜", "北向资金", "融资余额", "新股", "今日看点",
         "提示", "广告", "直播", "专栏")
SESSION_BONUS = {"盘后": 2, "夜间": 2, "非交易日": 2, "盘前": 1, "午间": 1, "盘中": 0}


def score(it: dict, names: dict[str, str]) -> tuple[int, dict]:
    text = f"{it.get('title', '')} {it.get('text', '')}"
    br: dict = {}
    nums = NUM.findall(text)
    br["精确数字"] = min(len(nums), 4)
    kw = 0
    hits = []
    for w, words in KEYWORDS.items():
        for k in words:
            if k in text:
                kw += w
                hits.append(k)
    br["催化词"] = min(kw, 8)
    br["时点"] = SESSION_BONUS.get(it.get("session") or "", 0)
    stocks = set(it.get("stocks") or [])
    stocks |= {code for name, code in names.items() if len(name) >= 3 and name in text}
    br["A股映射"] = min(len(stocks), 3)
    br["多源"] = min(len(it.get("also", [])), 3)
    s = sum(br.values())
    if any(n in text[:30] for n in NOISE):
        s -= 6
    return s, {"breakdown": br, "keywords": hits[:8], "stocks": sorted(stocks)[:12]}


def mainline_hits(text: str, cases: list[dict]) -> list[str]:
    hits = []
    for c in cases:
        words = {w for w in re.split(r"[·\s，、/（）()]+", f"{c.get('mainline', '')} {c.get('title', '')}") if len(w) >= 2}
        if sum(1 for w in words if w in text) >= 2:
            hits.append(c["id"])
    return hits[:4]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=None)
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args(argv)

    day = args.date or today_cn()
    ddir = data_dir(day)
    if not (ddir / "news.json").exists():
        print(f"no {ddir / 'news.json'} — run collect_news.py first (or collect catalysts with web search)")
        return 2
    news = read_json(ddir / "news.json")
    quotes = read_json(ddir / "quotes.json")["quotes"] if (ddir / "quotes.json").exists() else {}
    lookup = read_json(ddir / "lookup.json")["stocks"] if (ddir / "lookup.json").exists() else {}
    market = read_json(ddir / "market.json") if (ddir / "market.json").exists() else {}
    idx = ((market.get("indices") or {}).get("上证指数") or {}).get("pct")
    names = {q.get("name"): code for code, q in quotes.items() if q.get("name")}
    cases = load_cases()

    scored = []
    for it in news.get("items", []):
        s, info = score(it, names)
        info["mainline"] = mainline_hits(f"{it.get('title', '')} {it.get('text', '')}", cases)
        scored.append((s, it, info))
    scored.sort(key=lambda x: -x[0])
    top = scored[: args.top]

    def move(code: str) -> str:
        q = quotes.get(code) or lookup.get(code)
        if not q or q.get("pct") is None:
            return code
        ex = f"，超额 {q['pct'] - idx:+.2f}pct" if idx is not None else ""
        return f"{q.get('name', code)} {q['pct']:+.2f}%{ex}"

    lines = [f"# 候选催化 · {day}", "",
             f"窗口 {news.get('window')} · 共 {len(news.get('items', []))} 条 · 来源状态 {news.get('status')}", "",
             "打分 = 精确数字 + 催化词 + 时点(盘后/夜间/非交易日加分=预期差) + A股映射 + 多源；仅供初筛。", ""]
    out = []
    for rank, (s, it, info) in enumerate(top, 1):
        mv = "；".join(move(c) for c in info["stocks"][:6])
        ml = f" · 主线更新候选：{', '.join(info['mainline'])}" if info["mainline"] else ""
        lines += [f"## {rank}. [{s}] {it.get('title')}",
                  f"- {it.get('time')} {it.get('session')} · {it.get('source')}{' +' + '/'.join(it['also']) if it.get('also') else ''}{ml}",
                  f"- 打分 {info['breakdown']} · 关键词 {'、'.join(info['keywords'])}",
                  f"- 盘面：{mv or '（未识别到 A 股标的）'}",
                  f"- {it.get('text', '')[:300]}", ""]
        out.append({"rank": rank, "score": s, **info, "item": it})
    (ddir / "candidates.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(ddir / "candidates.json", {"report_date": day, "candidates": out})
    print(f"{len(out)} candidates -> {ddir / 'candidates.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
