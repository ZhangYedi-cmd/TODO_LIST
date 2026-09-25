#!/usr/bin/env python3
"""Collect the day's A-share market data (复盘数据) into the archive data dir.

    python3 collect_market.py [--date YYYY-MM-DD] [--skip-members]

Writes
  data/YYYYMMDD/market.json   indices, breadth, limit-up/down/broken pools,
                              涨停题材地图, concept & industry board ranks
  data/YYYYMMDD/quotes.json   every A-share: price, pct, amount, turnover,
                              float cap, PE(TTM), 60d/YTD pct, main net inflow

Sources (all public web endpoints, no key needed): Eastmoney push2/push2ex,
optionally 10jqka for 涨停原因.  Each source is independent; failures are
recorded under "status" so the analysis step knows what to fall back on.
Live quotes are only "today's close" after 15:00 CST; for a past date the
Eastmoney snapshot endpoints cannot go back in time, so the script refuses to
label a stale snapshot with an old date (quotes are then taken from K-lines
for the stocks you look up later with stock_lookup.py).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import (  # noqa: E402
    NetworkBlocked, data_dir, http_json, is_trading_day, last_trading_day, now_cn, today_cn, write_json,
)

UT = "bd1d9ddb04089700cf9c27f6f7426281"
UT_EX = "7eea3edcaed734bea9cbfc24409ed989"
INDICES = {
    "1.000001": "上证指数", "0.399001": "深证成指", "0.399006": "创业板指",
    "1.000688": "科创50", "1.000300": "沪深300", "0.899050": "北证50",
}
A_SHARES = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
STOCK_FIELDS = "f2,f3,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f62,f100,f115"
BOARD_FIELDS = "f2,f3,f6,f8,f12,f14,f20,f104,f105,f128,f136,f140"


def num(v):
    return None if v in (None, "-", "") else v


def secid(code: str) -> str:
    return ("1." if code[:1] in ("5", "6", "9") else "0.") + code


def clist(fs: str, fields: str, fid: str = "f3", po: int = 1, page_size: int = 100, max_pages: int = 80) -> list[dict]:
    """Page through Eastmoney's list endpoint (it caps page size at 100)."""
    out: list[dict] = []
    for pn in range(1, max_pages + 1):
        js = http_json("https://push2.eastmoney.com/api/qt/clist/get", params={
            "pn": pn, "pz": page_size, "po": po, "np": 1, "fltt": 2, "invt": 2, "fid": fid,
            "fs": fs, "fields": fields, "ut": UT,
        })
        data = js.get("data") or {}
        diff = data.get("diff") or []
        if isinstance(diff, dict):
            diff = list(diff.values())
        out.extend(diff)
        total = data.get("total") or 0
        if not diff or len(out) >= total:
            break
        time.sleep(0.15)
    return out


def fetch_indices() -> dict:
    js = http_json("https://push2.eastmoney.com/api/qt/ulist.np/get", params={
        "fltt": 2, "invt": 2, "fields": "f2,f3,f4,f6,f12,f13,f14", "secids": ",".join(INDICES), "ut": UT,
    })
    out = {}
    for d in (js.get("data") or {}).get("diff") or []:
        key = f"{d['f13']}.{d['f12']}"
        out[INDICES.get(key, d.get("f14"))] = {"code": d["f12"], "close": num(d.get("f2")),
                                               "pct": num(d.get("f3")), "amount": num(d.get("f6"))}
    return out


def index_last_bar_date() -> str | None:
    js = http_json("https://push2his.eastmoney.com/api/qt/stock/kline/get", params={
        "secid": "1.000001", "fields1": "f1,f2,f3", "fields2": "f51,f52,f53", "klt": 101, "fqt": 0,
        "end": "20500101", "lmt": 1, "ut": UT,
    })
    kl = ((js.get("data") or {}).get("klines") or [])
    return kl[-1].split(",")[0] if kl else None


def fetch_quotes() -> dict:
    rows = clist(A_SHARES, STOCK_FIELDS, fid="f12", po=0)
    quotes = {}
    for d in rows:
        code = d.get("f12")
        if not code:
            continue
        quotes[code] = {
            "name": d.get("f14"), "price": num(d.get("f2")), "pct": num(d.get("f3")),
            "volume": num(d.get("f5")), "amount": num(d.get("f6")), "amplitude": num(d.get("f7")),
            "turnover": num(d.get("f8")), "pe_dyn": num(d.get("f9")), "vol_ratio": num(d.get("f10")),
            "high": num(d.get("f15")), "low": num(d.get("f16")), "open": num(d.get("f17")),
            "prev_close": num(d.get("f18")), "total_cap": num(d.get("f20")), "float_cap": num(d.get("f21")),
            "pb": num(d.get("f23")), "pct_60d": num(d.get("f24")), "pct_ytd": num(d.get("f25")),
            "main_inflow": num(d.get("f62")), "industry": d.get("f100"), "pe_ttm": num(d.get("f115")),
        }
    return quotes


def fetch_boards(kind: str, top: int = 30) -> dict:
    fs = {"concept": "m:90+t:3+f:!50", "industry": "m:90+t:2+f:!50"}[kind]
    rows = clist(fs, BOARD_FIELDS, fid="f3", po=1, max_pages=8)
    boards = [{
        "code": d.get("f12"), "name": d.get("f14"), "pct": num(d.get("f3")), "amount": num(d.get("f6")),
        "turnover": num(d.get("f8")), "up": d.get("f104"), "down": d.get("f105"),
        "leader": d.get("f128"), "leader_code": d.get("f140"), "leader_pct": num(d.get("f136")),
    } for d in rows if d.get("f14")]
    boards = [b for b in boards if b["pct"] is not None]
    boards.sort(key=lambda b: b["pct"], reverse=True)
    return {"count": len(boards), "top": boards[:top], "bottom": boards[-top:][::-1]}


def pool(kind: str, day: str) -> list[dict]:
    path = {"zt": "getTopicZTPool", "zb": "getTopicZBPool", "dt": "getTopicDTPool"}[kind]
    sort = {"zt": "fbt:asc", "zb": "fbt:asc", "dt": "fund:asc"}[kind]
    js = http_json(f"https://push2ex.eastmoney.com/{path}", params={
        "ut": UT_EX, "dpt": "wz.ztzt", "Pageindex": 0, "pagesize": 10000, "sort": sort, "date": day.replace("-", ""),
    })
    rows = ((js.get("data") or {}).get("pool")) or []
    out = []
    for r in rows:
        item = {
            "code": r.get("c"), "name": r.get("n"),
            "price": (r.get("p") or 0) / 1000 if r.get("p") is not None else None,
            "pct": r.get("zdp"), "amount": r.get("amount"), "float_cap": r.get("ltsz"),
            "turnover": r.get("hs"), "industry": r.get("hybk"),
        }
        if kind == "zt":
            zt = r.get("zttj") or {}
            item.update({"boards": r.get("lbc"), "first_time": r.get("fbt"), "last_time": r.get("lbt"),
                         "seal_fund": r.get("fund"), "broken_times": r.get("zbc"),
                         "stat": f"{zt.get('days')}天{zt.get('ct')}板" if zt else None})
        elif kind == "zb":
            item.update({"broken_times": r.get("zbc"), "first_time": r.get("fbt"), "amplitude": r.get("zf")})
        else:
            item.update({"days": r.get("days"), "open_times": r.get("oc"), "seal_fund": r.get("fund")})
        out.append(item)
    return out


def ths_reasons(day: str) -> dict:
    """涨停原因 from 10jqka (optional): {code: '题材A+题材B'}."""
    out: dict = {}
    for page in range(1, 6):
        js = http_json("https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool", params={
            "page": page, "limit": 200,
            "field": "199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004",
            "filter": "HS,GEM2STAR", "order_field": "330324", "order_type": 0, "date": day.replace("-", ""),
        }, headers={"Referer": "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"})
        info = ((js.get("data") or {}).get("info")) or []
        for r in info:
            if r.get("code"):
                out[r["code"]] = {"reason": r.get("reason_type"), "high_days": r.get("high_days")}
        if len(info) < 200:
            break
    return out


def theme_map(zt: list[dict], reasons: dict) -> list[dict]:
    """Group limit-up stocks into 涨停题材地图 (by 10jqka reason when available, else industry)."""
    groups: dict[str, list] = {}
    for s in zt:
        r = (reasons.get(s["code"]) or {}).get("reason")
        keys = [k for k in (r or "").replace("＋", "+").split("+") if k] or [s.get("industry") or "其他"]
        for k in keys[:2]:
            groups.setdefault(k.strip(), []).append(s)
    themes = [{
        "theme": k, "count": len(v),
        "stocks": [f"{x['name']}({x['code']}){' ' + str(x['boards']) + '板' if (x.get('boards') or 1) > 1 else ''}"
                   for x in sorted(v, key=lambda x: -(x.get("boards") or 1))],
    } for k, v in groups.items()]
    themes.sort(key=lambda t: -t["count"])
    return themes


def breadth(quotes: dict) -> dict:
    pcts = [q["pct"] for q in quotes.values() if isinstance(q.get("pct"), (int, float)) and q.get("amount")]
    amount = sum(q["amount"] for q in quotes.values() if isinstance(q.get("amount"), (int, float)))
    return {"up": sum(p > 0 for p in pcts), "down": sum(p < 0 for p in pcts), "flat": sum(p == 0 for p in pcts),
            "amount_yi": round(amount / 1e8, 1) if amount else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=None, help="report date (default: today, CST)")
    ap.add_argument("--no-ths", action="store_true", help="skip 10jqka 涨停原因")
    args = ap.parse_args(argv)

    day = args.date or today_cn()
    trade_day = last_trading_day(day)
    out_dir = data_dir(day)
    status: dict[str, str] = {}
    market: dict = {"report_date": day, "trade_date": trade_day, "generated_at": now_cn().isoformat(timespec="seconds"),
                    "is_trading_day": is_trading_day(day), "status": status}

    def run(name, fn, *a):
        try:
            v = fn(*a)
            status[name] = "ok"
            return v
        except NetworkBlocked as e:
            status[name] = f"blocked: {e}"
        except Exception as e:  # noqa: BLE001 - every source is optional
            status[name] = f"error: {type(e).__name__}: {e}"
        return None

    last_bar = run("index_kline", index_last_bar_date)
    live_is_trade_day = last_bar == trade_day
    snapshot_ok = live_is_trade_day and (trade_day != today_cn() or now_cn().strftime("%H:%M") >= "15:05")
    market["snapshot_matches_trade_date"] = bool(snapshot_ok)

    quotes = None
    if snapshot_ok:
        market["indices"] = run("indices", fetch_indices)
        quotes = run("quotes", fetch_quotes)
        if quotes:
            market["breadth"] = breadth(quotes)
        market["concept_boards"] = run("concept_boards", fetch_boards, "concept")
        market["industry_boards"] = run("industry_boards", fetch_boards, "industry")
    else:
        status["snapshot"] = (f"skipped: live snapshot is for {last_bar}, not {trade_day}" if last_bar
                              else "skipped: could not confirm the latest trading date")

    # the limit-up/down pools are served per date, so they work for past days too
    zt = run("zt_pool", pool, "zt", trade_day) or []
    market["limit_up"] = zt
    market["limit_down"] = run("dt_pool", pool, "dt", trade_day) or []
    market["broken"] = run("zb_pool", pool, "zb", trade_day) or []
    reasons = {} if args.no_ths else (run("ths_reasons", ths_reasons, trade_day) or {})
    for s in zt:
        if s["code"] in reasons:
            s["reason"] = reasons[s["code"]]["reason"]
            s["high_days"] = reasons[s["code"]]["high_days"]
    market["limit_up_count"] = len(zt)
    market["theme_map"] = theme_map(zt, reasons) if zt else []

    write_json(out_dir / "market.json", market)
    if quotes:
        write_json(out_dir / "quotes.json", {"trade_date": trade_day, "quotes": quotes})
    ok = sum(v == "ok" for v in status.values())
    print(f"market data -> {out_dir}  ({ok}/{len(status)} sources ok)")
    for k, v in status.items():
        if v != "ok":
            print(f"  {k}: {v}")
    if any(v.startswith("blocked") for v in status.values()):
        print("NETWORK BLOCKED: allow *.eastmoney.com (push2, push2ex, push2his) and data.10jqka.com.cn, "
              "or fall back to web search for market data.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
