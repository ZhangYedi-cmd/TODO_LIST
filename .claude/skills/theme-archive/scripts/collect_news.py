#!/usr/bin/env python3
"""Collect the catalyst feed for a report date: 7x24 flashes, broker reports, announcements.

    python3 collect_news.py [--date YYYY-MM-DD] [--since "YYYY-MM-DD HH:MM"]

Writes data/YYYYMMDD/news.json with one list of items:
  {source, time, session, title, text, stocks, url?}
and data/YYYYMMDD/reports.json (broker research titles + ratings).

The window defaults to: previous trading day 15:00 -> report date 23:59, so
post-close and overnight news that the market has NOT priced yet is included
(盘后/夜间 items are exactly where 预期差 comes from).

Sources: 财联社电报, 东方财富 7x24, 新浪 7x24, 东财研报中心, 巨潮公告 (keyword
filtered).  Each is optional; failures are recorded under "status".
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import (  # noqa: E402
    CN_TZ, NetworkBlocked, data_dir, http_json, now_cn, prev_trading_day, session_of, strip_tags, today_cn,
    write_json,
)

ANN_KEYWORDS = ("涨价", "调价", "提价", "价格调整", "订单", "中标", "合同", "扩产", "投产", "停产", "减产",
                "异常波动", "严重异常", "业绩预告", "业绩快报", "重大资产", "收购", "回购", "增持", "问询函",
                "立案", "留置", "冻结", "战略合作", "定点", "认证", "获批", "临床", "授权", "许可")


def parse_ts(v) -> str | None:
    """Epoch seconds/ms or 'YYYY-MM-DD HH:MM:SS' -> 'YYYY-MM-DD HH:MM:SS' (CST)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        x = float(v)
        if x > 1e12:
            x /= 1000
        return dt.datetime.fromtimestamp(x, CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    return str(v)[:19].replace("T", " ")


def item(source, ts, title, text, stocks=None, url=None):
    ts = parse_ts(ts)
    text = strip_tags(text or "").strip()
    title = strip_tags(title or "").strip()
    if not title:
        m = re.match(r"^【(.+?)】", text)
        title = m.group(1) if m else text[:40]
    return {"source": source, "time": ts, "session": session_of(ts) if ts else None,
            "title": title, "text": text, "stocks": stocks or [], "url": url}


# ---------------------------------------------------------------- sources
def cls_sign(params: dict) -> str:
    qs = urllib.parse.urlencode(sorted(params.items()))
    return hashlib.md5(hashlib.sha1(qs.encode()).hexdigest().encode()).hexdigest()


def fetch_cls(start: str, end: str) -> list[dict]:
    """财联社电报, paging backwards from `end` until `start`."""
    out: list[dict] = []
    last = int(dt.datetime.fromisoformat(end).replace(tzinfo=CN_TZ).timestamp())
    for _ in range(40):
        params = {"app": "CailianpressWeb", "category": "", "lastTime": last, "last_time": last, "os": "web",
                  "refresh_type": 1, "rn": 50, "sv": "8.4.6"}
        params["sign"] = cls_sign(params)
        js = http_json("https://www.cls.cn/nodeapi/telegraphList", params=params,
                       headers={"Referer": "https://www.cls.cn/telegraph"})
        rows = ((js.get("data") or {}).get("roll_data")) or []
        if not rows:
            break
        for r in rows:
            stocks = [s.get("StockID") or s.get("stock_id") for s in (r.get("stock_list") or []) if isinstance(s, dict)]
            out.append(item("财联社", r.get("ctime"), r.get("title"), r.get("content") or r.get("brief"),
                            [s for s in stocks if s], r.get("shareurl")))
        oldest = min(int(r.get("ctime") or last) for r in rows)
        if oldest >= last or parse_ts(oldest) < start:
            break
        last = oldest
        time.sleep(0.3)
    return out


def fetch_em724(start: str) -> list[dict]:
    """东方财富 7x24 快讯."""
    out: list[dict] = []
    sort_end = ""
    for _ in range(30):
        js = None
        for host in ("np-listapi.eastmoney.com", "np-weblist.eastmoney.com"):
            try:
                js = http_json(f"https://{host}/comm/web/getFastNewsList", params={
                    "client": "web", "biz": "web_724", "fastColumn": "102", "sortEnd": sort_end,
                    "pageSize": 200, "req_trace": int(time.time() * 1000)})
                break
            except NetworkBlocked:
                raise
            except Exception:  # noqa: BLE001 - try the mirror host
                continue
        rows = (((js or {}).get("data") or {}).get("fastNewsList")) or []
        if not rows:
            break
        for r in rows:
            stocks = [s.split(".")[-1] for s in (r.get("stockList") or []) if isinstance(s, str)]
            out.append(item("东财7x24", r.get("showTime"), r.get("title"), r.get("summary"), stocks,
                            f"https://finance.eastmoney.com/a/{r.get('code')}.html" if r.get("code") else None))
        sort_end = (js.get("data") or {}).get("sortEnd") or rows[-1].get("realSort") or ""
        if not sort_end or (parse_ts(rows[-1].get("showTime")) or "9999") < start:
            break
        time.sleep(0.3)
    return out


def fetch_sina(start: str) -> list[dict]:
    """新浪财经 7x24."""
    out: list[dict] = []
    for page in range(1, 30):
        js = http_json("https://zhibo.sina.com.cn/api/zhibo/feed", params={
            "page": page, "page_size": 100, "zhibo_id": 152, "tag_id": 0, "dire": "f", "dpc": 1, "type": 0})
        rows = ((((js.get("result") or {}).get("data") or {}).get("feed") or {}).get("list")) or []
        if not rows:
            break
        for r in rows:
            out.append(item("新浪7x24", r.get("create_time"), "", r.get("rich_text")))
        if (parse_ts(rows[-1].get("create_time")) or "9999") < start:
            break
        time.sleep(0.3)
    return out


def fetch_reports(day: str) -> list[dict]:
    """东财研报中心: stock (qType=0) and industry (qType=1) reports published on `day`."""
    out: list[dict] = []
    for qtype in (0, 1):
        for page in range(1, 6):
            js = http_json("https://reportapi.eastmoney.com/report/list", params={
                "industryCode": "*", "pageSize": 100, "industry": "*", "rating": "*", "ratingChange": "*",
                "beginTime": day, "endTime": day, "pageNo": page, "fields": "", "qType": qtype, "orgCode": "",
                "code": "*", "rcode": "", "p": page, "pageNum": page, "pageNumber": page,
                "_": int(time.time() * 1000)})
            rows = js.get("data") or []
            for r in rows:
                out.append({
                    "kind": "个股" if qtype == 0 else "行业", "title": r.get("title"), "org": r.get("orgSName"),
                    "stock": r.get("stockName"), "code": r.get("stockCode"),
                    "industry": r.get("indvInduName") or r.get("industryName"),
                    "rating": r.get("emRatingName"), "date": (r.get("publishDate") or "")[:10],
                })
            if len(rows) < 100:
                break
            time.sleep(0.3)
    return out


def fetch_announcements(day: str) -> list[dict]:
    """巨潮资讯 announcements for `day`, keyword-filtered to catalyst types."""
    out: list[dict] = []
    for column in ("szse", "sse"):
        for page in range(1, 40):
            js = http_json("https://www.cninfo.com.cn/new/hisAnnouncement/query", data={
                "pageNum": page, "pageSize": 30, "column": column, "tabName": "fulltext", "plate": "",
                "stock": "", "searchkey": "", "secid": "", "category": "", "trade": "",
                "seDate": f"{day}~{day}", "sortName": "", "sortType": "", "isHLtitle": "true"},
                headers={"Referer": "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search"})
            rows = js.get("announcements") or []
            for r in rows:
                title = strip_tags(r.get("announcementTitle") or "")
                if any(k in title for k in ANN_KEYWORDS):
                    out.append(item("巨潮公告", r.get("announcementTime"), f"{r.get('secName')}：{title}", title,
                                    [r.get("secCode")], "https://static.cninfo.com.cn/" + (r.get("adjunctUrl") or "")))
            if not js.get("hasMore"):
                break
            time.sleep(0.3)
    return out


# ---------------------------------------------------------------- dedupe
def bigrams(s: str) -> set:
    s = re.sub(r"\W", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def dedupe(items: list[dict]) -> list[dict]:
    items = sorted(items, key=lambda x: x.get("time") or "")
    kept: list[dict] = []
    sigs: list[set] = []
    for it in items:
        b = bigrams(it["title"] + it["text"][:80])
        dup = next((k for k, s in zip(kept, sigs) if b and s and len(b & s) / len(b | s) > 0.6), None)
        if dup is not None:
            dup.setdefault("also", []).append(it["source"])
            continue
        kept.append(it)
        sigs.append(b)
    return kept


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=None, help="report date (default: today, CST)")
    ap.add_argument("--since", default=None, help="window start 'YYYY-MM-DD HH:MM' (default: prev trading day 15:00)")
    args = ap.parse_args(argv)

    day = args.date or today_cn()
    start = args.since or f"{prev_trading_day(day)} 15:00:00"
    end = f"{day} 23:59:59"
    status: dict[str, str] = {}
    items: list[dict] = []

    def run(name, fn, *a):
        try:
            v = fn(*a)
            status[name] = f"ok ({len(v)})"
            return v
        except NetworkBlocked as e:
            status[name] = f"blocked: {e}"
        except Exception as e:  # noqa: BLE001
            status[name] = f"error: {type(e).__name__}: {e}"
        return []

    items += run("cls", fetch_cls, start, end)
    items += run("em724", fetch_em724, start)
    items += run("sina", fetch_sina, start)
    items += run("announcements", fetch_announcements, day)
    items = [i for i in items if i.get("time") and start <= i["time"] <= end]
    items = dedupe(items)
    reports = run("reports", fetch_reports, day)

    out_dir = data_dir(day)
    write_json(out_dir / "news.json", {"report_date": day, "window": [start, end],
                                       "generated_at": now_cn().isoformat(timespec="seconds"),
                                       "status": status, "items": items})
    write_json(out_dir / "reports.json", {"report_date": day, "status": status.get("reports"), "items": reports})
    print(f"news -> {out_dir}  ({len(items)} items after dedupe, {len(reports)} broker reports)")
    for k, v in status.items():
        print(f"  {k}: {v}")
    if all(v.startswith("blocked") for v in status.values()):
        print("NETWORK BLOCKED: allow www.cls.cn, np-listapi.eastmoney.com, zhibo.sina.com.cn, "
              "reportapi.eastmoney.com, www.cninfo.com.cn — or collect catalysts with web search.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
