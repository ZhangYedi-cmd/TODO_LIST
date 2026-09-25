#!/usr/bin/env python3
"""One entry point for the daily run.

    python3 daily.py prepare [--date YYYY-MM-DD] [--force]   # steps 0-2: calendar, collect, screen
    python3 daily.py status                                  # archive by 主线 (what exists, last update)
    python3 daily.py finish  [--date YYYY-MM-DD]             # validate the day's cases, build the HTML

Exit codes: 0 ok · 1 validation errors · 2 data sources blocked (fallback to
web search) · 3 not a trading day (scheduled runs stop here unless --force).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ta_common import (  # noqa: E402
    archive_home, calendar_known, cases_dir, data_dir, dist_dir, is_trading_day, last_trading_day, load_cases,
    read_json, today_cn,
)


def run(script: str, *args: str) -> int:
    return subprocess.run([sys.executable, str(HERE / script), *args]).returncode


def cmd_prepare(a) -> int:
    day = a.date or today_cn()
    print(f"== 题材档案库 · {day} · archive {archive_home()}")
    if not calendar_known(day):
        print(f"! trading calendar has no holiday list for {day[:4]} — add it to ta_common.EXCHANGE_HOLIDAYS")
    if not is_trading_day(day):
        print(f"{day} is not an A-share trading day (last trading day {last_trading_day(day)}).")
        if not a.force:
            print("Stopping: scheduled runs only report on trading days. Use --force to write anyway.")
            return 3
    n = len(list(cases_dir().glob("*.json"))) if cases_dir().exists() else 0
    print(f"archive: {n} cases" + ("" if n else " — empty; seed it with import_html.py <existing archive.html> if you have one"))
    rc_m = run("collect_market.py", "--date", day)
    rc_n = run("collect_news.py", "--date", day)
    if (data_dir(day) / "news.json").exists():
        run("screen_candidates.py", "--date", day)
    m = data_dir(day) / "market.json"
    if m.exists():
        mk = read_json(m)
        idx = mk.get("indices") or {}
        line = " · ".join(f"{k} {v['pct']:+.2f}%" for k, v in idx.items() if v and v.get("pct") is not None)
        if line:
            print(f"\n{mk['trade_date']} 收盘：{line}")
        if mk.get("breadth"):
            b = mk["breadth"]
            print(f"涨 {b['up']} / 跌 {b['down']} / 平 {b['flat']} · 成交 {b['amount_yi']} 亿 · 涨停 {mk.get('limit_up_count')} 家")
        for t in (mk.get("theme_map") or [])[:8]:
            print(f"  题材 {t['theme']} ×{t['count']}: {'、'.join(t['stocks'][:6])}")
    if rc_m == 2 or rc_n == 2:
        print("\nDATA FALLBACK: collectors were blocked — gather catalysts and 盘面 numbers with web search "
              "(references/data-sources.md § Web-search fallback) and note 'Web 检索' in sources.")
        return 2
    return 0


def cmd_status(a) -> int:
    cases = load_cases()
    if not cases:
        print(f"no cases in {cases_dir()}")
        return 0
    by: dict[str, list] = {}
    for c in cases:
        by.setdefault(c.get("mainline", "?"), []).append(c)
    for ml, cs in sorted(by.items(), key=lambda kv: -max(c["date"] for c in kv[1])):
        print(f"\n## {ml} ({len(cs)})")
        for c in sorted(cs, key=lambda c: c["date"], reverse=True):
            last = max([t.get("when", "")[:10] for t in c.get("timeline", [])] + [c["date"]])
            print(f"- {c['date']} {c['id']} · {c['grade']['text'][:28]} · {c['pricing']} · last update {last}")
            print(f"    {c.get('positionNote', '')[:90]}")
    return 0


def latest_quotes() -> dict:
    """Merge the newest quotes.json and lookup.json into {code: {price, float_cap, pct, date}}."""
    base = data_dir()
    if not base.exists():
        return {}
    out: dict = {}
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        q = d / "quotes.json"
        if q.exists():
            js = read_json(q)
            for code, v in js["quotes"].items():
                if v.get("price") and v.get("float_cap") and v.get("pct") is not None:
                    out[code] = {"price": v["price"], "float_cap": v["float_cap"], "pct": v["pct"], "date": js["trade_date"]}
        lk = d / "lookup.json"
        if lk.exists():
            for code, v in read_json(lk).get("stocks", {}).items():
                if v.get("price") and v.get("float_cap") and v.get("pct") is not None:
                    prev = out.get(code)
                    if not prev or prev["date"] <= v["trade_date"]:
                        out[code] = {"price": v["price"], "float_cap": v["float_cap"], "pct": v["pct"],
                                     "date": v["trade_date"]}
    if not out:
        return {}
    newest = max(v["date"] for v in out.values())
    return {k: v for k, v in out.items() if v["date"] == newest}


def cmd_finish(a) -> int:
    from build_archive import Opts, render_page

    day = a.date or today_cn()
    todays = [p for p in sorted(cases_dir().glob("*.json")) if read_json(p).get("date") == day]
    touched = [p for p in sorted(cases_dir().glob("*.json"))
               if any(t.get("when", "").startswith(day) for t in read_json(p).get("timeline", []))]
    files = sorted(set(todays) | set(touched))
    if files:
        rc = run("validate_case.py", *map(str, files))
        if rc:
            print("\nFix the ERRORs above, then run finish again.")
            return 1
    else:
        print(f"no case dated or updated {day}; rebuilding the archive only")
    cases = load_cases()
    quotes = latest_quotes()
    html = render_page(cases, Opts(quotes=quotes))
    out = dist_dir() / "题材档案库.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    dated = dist_dir() / f"题材档案库_{day.replace('-', '')}.html"
    shutil.copyfile(out, dated)
    print(f"\nbuilt {out} ({len(cases)} cases, {out.stat().st_size // 1024} KB; quotes refreshed for {len(quotes)} stocks)")
    print(f"copy  {dated}")
    for p in todays:
        c = read_json(p)
        print(f"  NEW    {c['id']} · {c['grade']['text']} · {c['pricing']}")
    for p in touched:
        if p not in todays:
            print(f"  UPDATE {read_json(p)['id']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--date")
    p.add_argument("--force", action="store_true")
    sub.add_parser("status")
    f = sub.add_parser("finish")
    f.add_argument("--date")
    a = ap.parse_args(argv)
    return {"prepare": cmd_prepare, "status": cmd_status, "finish": cmd_finish}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
