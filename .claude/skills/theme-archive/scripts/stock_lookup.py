#!/usr/bin/env python3
"""Look up stocks for the day and print them in house style (for writing cases).

    python3 stock_lookup.py 三安光电 600703 源杰科技 [--date YYYY-MM-DD] [--days 5] [--json]

For each stock prints: close, pct, 超额 (pct minus 上证 pct), amount, turnover,
float cap, PE(TTM), limit-up status, the last N daily moves, and two ready-made
strings:
  cap   -> "12.79 元 · 流通 638 亿 · 9/16 +2.81%"      (stock card quote line)
  盘面  -> "三安光电 12.43 元 -1.51%（超额 -2.22pct，成交 11.1 亿，换手 1.80%）"

Data: data/YYYYMMDD/quotes.json + market.json when collect_market.py ran,
otherwise live Eastmoney K-lines.  Results are cached to data/YYYYMMDD/lookup.json,
which validate_case.py and build_archive.py also read.

Fallback mode (hosts blocked): record numbers you verified via web search so the
build and the validator can use them exactly like fetched data:

    python3 stock_lookup.py --manual 601218 吉鑫科技 --pct 10.03 --price 6.25 \
        [--float-cap 61.2 (亿)] [--amount 9.8 (亿)] [--turnover 16.1] --index-pct -1.22 \
        --source "21财经 9/24" --date 2026-09-24
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import (  # noqa: E402
    NetworkBlocked, data_dir, http_json, last_trading_day, md, read_json, today_cn, write_json,
)

UT = "bd1d9ddb04089700cf9c27f6f7426281"


def secid(code: str) -> str:
    return ("1." if code[:1] in ("5", "6", "9") else "0.") + code


def resolve(term: str, quotes: dict) -> tuple[str, str] | None:
    if re.fullmatch(r"\d{6}", term):
        q = quotes.get(term)
        return term, (q or {}).get("name") or term
    for code, q in quotes.items():
        if q.get("name") == term:
            return code, term
    js = http_json("https://searchapi.eastmoney.com/api/suggest/get", params={
        "input": term, "type": 14, "token": "D43BF722C8E33BDC906FB84D85E326E8", "count": 5})
    for r in ((js.get("QuotationCodeTable") or {}).get("Data")) or []:
        if re.fullmatch(r"\d{6}", r.get("Code", "")) and r.get("SecurityTypeName") in ("沪A", "深A", "京A", "科创板", "创业板", None):
            return r["Code"], r.get("Name") or term
    return None


def klines(code: str, end: str, n: int, sid: str | None = None) -> list[dict]:
    js = http_json("https://push2his.eastmoney.com/api/qt/stock/kline/get", params={
        "secid": sid or secid(code), "fields1": "f1,f2,f3", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": 101, "fqt": 1, "end": end.replace("-", ""), "lmt": n, "ut": UT})
    out = []
    for k in ((js.get("data") or {}).get("klines")) or []:
        d, o, c, h, lo, vol, amt, amp, pct, chg, tr = k.split(",")
        out.append({"date": d, "open": float(o), "close": float(c), "high": float(h), "low": float(lo),
                    "amount": float(amt), "amplitude": float(amp), "pct": float(pct), "turnover": float(tr)})
    return out


def float_shares(code: str) -> float | None:
    js = http_json("https://push2.eastmoney.com/api/qt/stock/get", params={
        "secid": secid(code), "fields": "f57,f58,f84,f85,f116,f117,f162,f163,f164,f167", "fltt": 2, "invt": 2, "ut": UT})
    d = js.get("data") or {}
    return d.get("f85") if isinstance(d.get("f85"), (int, float)) else None


def fmt_amount(yuan: float | None) -> str:
    if not yuan:
        return "—"
    yi = yuan / 1e8
    return f"{yi:.2f} 亿" if yi < 10 else f"{yi:.1f} 亿"


def fmt_cap(price: float, float_cap: float | None, day: str, pct: float) -> str:
    parts = [f"{price:.2f} 元"]
    if float_cap:
        fc = float_cap / 1e8
        parts.append("流通 " + (f"{fc / 1e4:.2f} 万亿" if fc >= 1e4 else f"{fc:.0f} 亿"))
    parts.append(f"{md(day)} {pct:+.2f}%")
    return " · ".join(parts)


def record_manual(args, td: str, cache: dict, cache_path: Path) -> int:
    code, name = args.terms[0], args.terms[1] if len(args.terms) > 1 else args.terms[0]
    if not re.fullmatch(r"\d{6}", code) or args.pct is None:
        print("--manual needs: CODE NAME --pct X (and ideally --price, --index-pct, --source)")
        return 2
    idx = args.index_pct if args.index_pct is not None else cache.get("index_pct")
    if args.index_pct is not None:
        cache["index_pct"] = args.index_pct
    fcap = args.float_cap * 1e8 if args.float_cap else None
    rec = {"code": code, "name": name, "trade_date": td, "price": args.price, "pct": args.pct,
           "excess": round(args.pct - idx, 2) if idx is not None else None,
           "amount": args.amount * 1e8 if args.amount else None, "turnover": args.turnover,
           "float_cap": fcap, "source": f"manual: {args.source or 'web search'}", "path": []}
    rec["cap"] = fmt_cap(args.price, fcap, td, args.pct) if args.price else None
    parts = [f"超额 {rec['excess']:+.2f}pct" if rec["excess"] is not None else None,
             f"成交 {fmt_amount(rec['amount'])}" if rec["amount"] else None,
             f"换手 {args.turnover:.2f}%" if args.turnover is not None else None]
    price = f"{args.price:.2f} 元 " if args.price else ""
    rec["phrase"] = f"{name} {price}{args.pct:+.2f}%（{'，'.join(p for p in parts if p)}）"
    cache["stocks"][code] = rec
    write_json(cache_path, cache)
    print(f"recorded {rec['phrase']}" + (f"\n    cap: {rec['cap']}" if rec["cap"] else ""))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("terms", nargs="+", help="stock names or 6-digit codes (with --manual: CODE NAME)")
    ap.add_argument("--date", default=None, help="report date (default today CST); uses its last trading day")
    ap.add_argument("--days", type=int, default=5, help="daily moves to show (default 5)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--manual", action="store_true", help="record web-verified numbers instead of fetching")
    ap.add_argument("--pct", type=float, help="--manual: day pct change")
    ap.add_argument("--price", type=float, help="--manual: close price (元)")
    ap.add_argument("--float-cap", type=float, help="--manual: float market cap in 亿")
    ap.add_argument("--amount", type=float, help="--manual: turnover amount in 亿")
    ap.add_argument("--turnover", type=float, help="--manual: turnover rate %%")
    ap.add_argument("--index-pct", type=float, help="--manual: 上证 pct for the day (stored once per day)")
    ap.add_argument("--source", help="--manual: where the numbers came from")
    args = ap.parse_args(argv)

    day = args.date or today_cn()
    td = last_trading_day(day)
    ddir = data_dir(day)
    quotes = read_json(ddir / "quotes.json")["quotes"] if (ddir / "quotes.json").exists() else {}
    market = read_json(ddir / "market.json") if (ddir / "market.json").exists() else {}
    zt = {s["code"]: s for s in market.get("limit_up", [])}
    cache_path = ddir / "lookup.json"
    cache = read_json(cache_path) if cache_path.exists() else {"trade_date": td, "stocks": {}}
    if args.manual:
        return record_manual(args, td, cache, cache_path)

    idx_pct = ((market.get("indices") or {}).get("上证指数") or {}).get("pct")
    results, errors = [], []
    try:
        if idx_pct is None:
            bars = klines("000001", td, 1, sid="1.000001")
            idx_pct = bars[-1]["pct"] if bars and bars[-1]["date"] == td else None
    except NetworkBlocked as e:
        errors.append(f"index: {e}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"index: {e}")

    for term in args.terms:
        try:
            r = resolve(term, quotes)
            if not r:
                errors.append(f"{term}: not found")
                continue
            code, name = r
            q = quotes.get(code) or {}
            hist = []
            try:
                hist = [b for b in klines(code, td, args.days) if b["date"] <= td]
            except NetworkBlocked:
                raise
            except Exception:  # noqa: BLE001 - history is a bonus
                pass
            bar = hist[-1] if hist and hist[-1]["date"] == td else None
            price = q.get("price") if q else (bar or {}).get("close")
            pct = q.get("pct") if q else (bar or {}).get("pct")
            if price is None or pct is None:
                errors.append(f"{name}({code}): no bar for {td} (suspended?)")
                continue
            amount = q.get("amount") if q else (bar or {}).get("amount")
            turnover = q.get("turnover") if q else (bar or {}).get("turnover")
            fcap = q.get("float_cap")
            if not fcap:
                fs = float_shares(code)
                fcap = fs * price if fs else None
            excess = round(pct - idx_pct, 2) if idx_pct is not None else None
            rec = {
                "code": code, "name": name, "trade_date": td, "price": price, "pct": pct, "excess": excess,
                "amount": amount, "turnover": turnover, "float_cap": fcap, "pe_ttm": q.get("pe_ttm"),
                "vol_ratio": q.get("vol_ratio"), "amplitude": q.get("amplitude"), "pct_ytd": q.get("pct_ytd"),
                "pct_60d": q.get("pct_60d"), "main_inflow": q.get("main_inflow"),
                "limit_up": ({"boards": zt[code].get("boards"), "reason": zt[code].get("reason")} if code in zt else None),
                "path": [{"date": b["date"], "pct": b["pct"]} for b in hist],
            }
            rec["cap"] = fmt_cap(price, fcap, td, pct) if fcap else None
            parts = [f"超额 {excess:+.2f}pct" if excess is not None else None,
                     f"成交 {fmt_amount(amount)}" if amount else None,
                     f"换手 {turnover:.2f}%" if isinstance(turnover, (int, float)) else None]
            rec["phrase"] = f"{name} {price:.2f} 元 {pct:+.2f}%（{'，'.join(p for p in parts if p)}）"
            if len(hist) > 1:
                cum = 1.0
                for b in hist:
                    cum *= 1 + b["pct"] / 100
                rec["path_phrase"] = ("、".join(f"{md(b['date'])} {b['pct']:+.2f}%" for b in hist)
                                      + f"，{len(hist)} 日累计 {(cum - 1) * 100:+.1f}%")
            cache["stocks"][code] = rec
            results.append(rec)
        except NetworkBlocked as e:
            errors.append(f"{term}: blocked ({e}) — use web search: 「{term} {md(td)} 收盘 涨跌幅 成交额」")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{term}: {type(e).__name__}: {e}")

    if results:
        cache["index_pct"] = idx_pct
        write_json(cache_path, cache)
    if args.json:
        print(json.dumps({"index_pct": idx_pct, "results": results, "errors": errors}, ensure_ascii=False, indent=2))
    else:
        print(f"trade date {td} · 上证 {idx_pct:+.2f}%" if idx_pct is not None else f"trade date {td} · 上证 n/a")
        for r in results:
            lu = f" · 涨停{'(' + str(r['limit_up']['boards']) + '板)' if r['limit_up'] and r['limit_up'].get('boards') else ''}" if r["limit_up"] else ""
            print(f"- {r['phrase']}{lu}")
            if r.get("cap"):
                print(f"    cap: {r['cap']}")
            if r.get("path_phrase"):
                print(f"    path: {r['path_phrase']}")
            extra = {k: r[k] for k in ("pe_ttm", "vol_ratio", "amplitude", "pct_ytd", "pct_60d", "main_inflow") if r.get(k) is not None}
            if extra:
                print(f"    {extra}")
        for e in errors:
            print(f"! {e}")
    return 0 if results else 2


if __name__ == "__main__":
    raise SystemExit(main())
