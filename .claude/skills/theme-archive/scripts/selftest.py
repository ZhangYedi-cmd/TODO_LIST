#!/usr/bin/env python3
"""Offline self-test for the theme-archive skill.

    python3 selftest.py [--reference existing_archive.html]

1. validator accepts the sample case and rejects a fresh scaffold (TODOs)
2. renderer emits every section, fills quote lines, keeps the fixed markup
3. collectors / lookup / screening parse canned API payloads correctly
4. daily finish validates and builds
5. MCP client: handshake, JSON + SSE replies, pagination, tool calls, errors (local fake server)
6. with --reference: import -> legacy build reproduces the file byte for byte
No network needed; everything runs in a temp archive.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FIXTURE = HERE.parent / "tests" / "fixtures" / "sample_case.json"
FAILS: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a, **kw)
    return rc, buf.getvalue()


# ------------------------------------------------------------------ canned payloads
def fake_http_json(url: str, params=None, **kw):
    p = params or {}
    if "ulist.np" in url:
        return {"data": {"diff": [
            {"f2": 3888.37, "f3": -1.22, "f4": -48.1, "f6": 7.1e11, "f12": "000001", "f13": 1, "f14": "上证指数"},
            {"f2": 13316.97, "f3": -2.34, "f4": -319.0, "f6": 9.4e11, "f12": "399001", "f13": 0, "f14": "深证成指"}]}}
    if "clist/get" in url:
        if "m:90" in p.get("fs", ""):
            return {"data": {"total": 2, "diff": [
                {"f12": "BK1001", "f14": "示例概念A", "f3": 3.2, "f6": 1e10, "f8": 2.1, "f104": 30, "f105": 2,
                 "f128": "丁公司", "f140": "999004", "f136": 10.0},
                {"f12": "BK1002", "f14": "示例概念B", "f3": -1.5, "f6": 5e9, "f8": 1.1, "f104": 3, "f105": 40,
                 "f128": "甲公司", "f140": "999001", "f136": 1.0}]}}
        if p.get("pn", 1) > 1:
            return {"data": {"total": 2, "diff": []}}
        return {"data": {"total": 2, "diff": {"0": {
            "f12": "999001", "f14": "甲公司", "f2": 12.43, "f3": -1.51, "f5": 900000, "f6": 1.11e9, "f7": 3.2, "f8": 1.8,
            "f9": 30.1, "f10": 0.9, "f15": 12.9, "f16": 12.3, "f17": 12.8, "f18": 12.62, "f20": 6.4e10, "f21": 6.38e10,
            "f23": 2.1, "f24": 5.5, "f25": 12.0, "f62": -8.3e6, "f100": "半导体", "f115": 40.2},
            "1": {"f12": "999004", "f14": "丁公司", "f2": 5.5, "f3": 10.0, "f6": 3e8, "f8": 12.0, "f20": 3e9, "f21": 2.5e9}}}}
    if "kline/get" in url:
        if p.get("secid") == "1.000001":
            return {"data": {"klines": ["2026-09-24,3930.1,3888.37,3931.0,3880.2,1,1,1,-1.22,-48.1,1"]}}
        return {"data": {"klines": ["2026-09-23,12.5,12.62,12.7,12.4,1,1.0e9,2.4,0.96,0.12,1.7",
                                    "2026-09-24,12.8,12.43,12.9,12.3,1,1.11e9,4.75,-1.51,-0.19,1.8"]}}
    if "stock/get" in url:
        return {"data": {"f57": "999001", "f58": "甲公司", "f85": 5.13e9}}
    if "getTopicZTPool" in url:
        return {"data": {"tc": 1, "pool": [{"c": "999004", "n": "丁公司", "p": 5500, "zdp": 10.0, "amount": 3e8,
                                             "ltsz": 2.5e9, "hs": 12.0, "lbc": 2, "fbt": 93500, "lbt": 93500, "fund": 5e7,
                                             "zbc": 0, "hybk": "化工", "zttj": {"days": 2, "ct": 2}}]}}
    if "getTopicDTPool" in url or "getTopicZBPool" in url:
        return {"data": {"pool": []}}
    if "10jqka" in url:
        return {"data": {"info": [{"code": "999004", "reason_type": "示例涨价+示例概念", "high_days": "2天2板"}]}}
    if "searchapi" in url:
        return {"QuotationCodeTable": {"Data": [{"Code": "999001", "Name": "甲公司", "SecurityTypeName": "沪A"}]}}
    if "telegraphList" in url:
        if int(p.get("last_time", 0)) < 1758700000:
            return {"data": {"roll_data": []}}
        return {"data": {"roll_data": [
            {"ctime": 1758707000, "title": "示例材料集体涨价", "content": "【示例材料集体涨价】财联社9月24日电，示例龙头发布调价函，国内上调 800 元/吨，年内第三轮。",
             "stock_list": [{"StockID": "999001"}]},
            {"ctime": 1758690000, "title": "", "content": "【收评：三大指数集体下跌】沪指跌1.22%。"}]}}
    if "getFastNewsList" in url:
        return {"data": {"fastNewsList": [{"code": "202609241", "title": "示例材料价格创历史新高",
                                           "summary": "示例材料报价 12000 元/吨，较月初 +45%，创历史新高。",
                                           "showTime": "2026-09-24 18:10:00", "stockList": ["1.999001"], "realSort": "1"}],
                         "sortEnd": ""}}
    if "zhibo.sina" in url:
        return {"result": {"data": {"feed": {"list": [{"rich_text": "示例材料集体涨价，示例龙头上调 800 元/吨", "create_time": "2026-09-24 17:55:00"}]}}}}
    if "reportapi" in url:
        return {"data": [{"title": "示例行业深度", "orgSName": "示例证券", "stockName": "甲公司", "stockCode": "999001",
                          "emRatingName": "增持", "publishDate": "2026-09-24 00:00:00.000"}]}
    if "cninfo" in url:
        return {"announcements": [{"secCode": "999001", "secName": "甲公司", "announcementTitle": "关于产品价格调整的公告",
                                   "announcementTime": 1758704400000, "adjunctUrl": "x.PDF"}], "hasMore": False}
    raise AssertionError(f"unexpected url {url}")


def fake_mcp_server(token: str):
    """Local streamable-HTTP MCP server: session id, JSON and SSE replies, paginated tools/list, 401."""
    import http.server
    import threading

    tools = [{"name": "get_quote", "description": "行情", "inputSchema": {"type": "object",
              "properties": {"code": {"type": "string"}}, "required": ["code"]}},
             {"name": "get_kline", "inputSchema": {"type": "object", "properties": {}}},
             {"name": "get_news", "inputSchema": {"type": "object", "properties": {}}}]

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body=b"", ctype="application/json", extra=None):
            self.send_response(code)
            if body:
                self.send_header("Content-Type", ctype)
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_DELETE(self):
            self.send(200)

        def do_POST(self):
            msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.headers.get("Authorization") != token:
                return self.send(401, b'{"error": "invalid token"}')
            method, mid = msg.get("method"), msg.get("id")

            def reply(result):
                return json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}, ensure_ascii=False).encode()

            if method == "initialize":
                return self.send(200, reply({"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                                             "serverInfo": {"name": "fake-ifind", "version": "0.1"}}),
                                 extra={"Mcp-Session-Id": "sess-1"})
            if self.headers.get("Mcp-Session-Id") != "sess-1" or self.headers.get("MCP-Protocol-Version") != "2025-03-26":
                return self.send(400, b'{"error": "no session"}')
            if method == "notifications/initialized":
                return self.send(202)
            if method == "tools/list" and not (msg.get("params") or {}).get("cursor"):
                note = json.dumps({"jsonrpc": "2.0", "method": "notifications/message", "params": {"data": "hi"}})
                page = reply({"tools": tools[:2], "nextCursor": "p2"}).decode()
                body = f"event: message\ndata: {note}\n\nevent: message\ndata: {page}\n\n".encode()
                return self.send(200, body, "text/event-stream")
            if method == "tools/list":
                return self.send(200, reply({"tools": tools[2:]}))
            if method == "tools/call" and msg["params"]["name"] == "get_quote":
                text = json.dumps({"code": msg["params"]["arguments"]["code"], "close": 12.43}, ensure_ascii=False)
                return self.send(200, reply({"content": [{"type": "text", "text": text}], "isError": False}))
            err = {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool"}}
            return self.send(200, json.dumps(err).encode())

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", help="an existing archive HTML to round-trip")
    args = ap.parse_args(argv)

    tmp = Path(tempfile.mkdtemp(prefix="theme-archive-selftest-"))
    os.environ["THEME_ARCHIVE_HOME"] = str(tmp)
    import build_archive
    import collect_market
    import collect_news
    import new_case
    import screen_candidates
    import stock_lookup
    import validate_case
    from ta_common import cases_dir, data_dir, load_cases, read_json, write_json

    print("1. validator")
    sample = read_json(FIXTURE)
    rep = validate_case.validate(sample, {sample["id"]}, {})
    check(not rep.errors, f"sample case validates ({rep.errors[:2]})")
    bad = dict(sample, pricing="已部分定价")
    check(any("pricing" in e for e in validate_case.validate(bad, set(), {}).errors), "off-enum pricing rejected")
    bad = json.loads(json.dumps(sample))
    bad["facts"][0]["value"] += "，建议逢低买入"
    check(any("advice" in e for e in validate_case.validate(bad, set(), {}).errors), "advice wording rejected")
    rc, _ = quiet(new_case.main, ["scaffold-test", "--title", "脚手架", "--date", "2026-09-24"])
    sc = read_json(cases_dir() / "scaffold-test.json")
    check(rc == 0 and any("TODO" in e for e in validate_case.validate(sc, set(), {}).errors), "scaffold fails until TODOs are filled")
    (cases_dir() / "scaffold-test.json").unlink()

    print("2. renderer")
    write_json(cases_dir() / f"{sample['id']}.json", sample)
    quotes = {"999001": {"price": 12.43, "float_cap": 6.38e10, "pct": -1.51, "date": "2026-09-24"}}
    html = build_archive.render_page(load_cases(), build_archive.Opts(quotes=quotes))
    for h2 in ("核心事实", "主线更新（多段催化时间线）", "逻辑推演", "产业链逻辑链条", "环节 × 标的 × 映射逻辑",
               "合规决策链 · 八要素", "情景推演", "信号对照台", "跟踪日历"):
        check(f'<span class="p">&gt;</span>{h2}</h2>' in html, f"section {h2}")
    check('<span class="cap">12.43 元 · 流通 638 亿 · 9/24 -1.51%</span>' in html, "quote line refreshed from quotes")
    check('<div class="gene">🧬 题材基因：' in html and '<div class="confirm">✔ 确认：' in html, "fixed prefixes added")
    check('<div class="stat b"><div class="v">1</div>' in html, "index stats count the case")
    check(html.count('class="card-c"') == 1 and "#fixture-sample-case" in html, "index card links to case")

    print("3. collectors (canned payloads)")
    for mod in (collect_market, collect_news, stock_lookup):
        mod.http_json = fake_http_json
    collect_market.time.sleep = lambda *_: None
    collect_news.time.sleep = lambda *_: None
    idx = collect_market.fetch_indices()
    check(idx.get("上证指数", {}).get("pct") == -1.22, "indices parsed")
    q = collect_market.fetch_quotes()
    check(q["999001"]["float_cap"] == 6.38e10 and q["999001"]["pe_ttm"] == 40.2, "quotes parsed (dict-shaped diff)")
    zt = collect_market.pool("zt", "2026-09-24")
    check(zt and zt[0]["boards"] == 2 and zt[0]["price"] == 5.5, "limit-up pool parsed")
    tm = collect_market.theme_map(zt, collect_market.ths_reasons("2026-09-24"))
    check(tm and tm[0]["theme"] == "示例涨价", "涨停题材地图 grouped by 10jqka reason")
    boards = collect_market.fetch_boards("concept")
    check(boards["top"][0]["name"] == "示例概念A", "board ranks parsed")
    cls = collect_news.fetch_cls("2026-09-23 15:00:00", "2026-09-24 23:59:59")
    check(any("涨价" in i["title"] and i["session"] == "盘后" for i in cls), "财联社 parsed with session tag")
    em = collect_news.fetch_em724("2026-09-23 15:00:00")
    check(em and em[0]["stocks"] == ["999001"], "东财7x24 parsed")
    sina = collect_news.fetch_sina("2026-09-23 15:00:00")
    ann = collect_news.fetch_announcements("2026-09-24")
    check(ann and "价格调整" in ann[0]["title"], "巨潮公告 keyword filter")
    items = collect_news.dedupe(cls + em + sina + ann)
    check(len(items) < len(cls + em + sina + ann), "cross-source dedupe")
    rep_ = collect_news.fetch_reports("2026-09-24")
    check(rep_ and rep_[0]["rating"] == "增持", "broker reports parsed")

    ddir = data_dir("2026-09-24")
    write_json(ddir / "news.json", {"window": ["2026-09-23 15:00:00", "2026-09-24 23:59:59"], "status": {}, "items": items})
    write_json(ddir / "quotes.json", {"trade_date": "2026-09-24", "quotes": q})
    write_json(ddir / "market.json", {"trade_date": "2026-09-24", "indices": idx, "limit_up": zt})
    rc, out = quiet(stock_lookup.main, ["甲公司", "999004", "--date", "2026-09-24"])
    lk = read_json(ddir / "lookup.json")["stocks"]
    check(rc == 0 and lk["999001"]["excess"] == -0.29, "lookup computes excess vs 上证")
    check(lk["999001"]["cap"] == "12.43 元 · 流通 638 亿 · 9/24 -1.51%", "lookup cap line in house format")
    check("2 日累计" in lk["999001"].get("path_phrase", ""), "lookup multi-day path")
    rc, _ = quiet(screen_candidates.main, ["--date", "2026-09-24"])
    cands = read_json(ddir / "candidates.json")["candidates"]
    check(rc == 0 and cands and "收评" not in cands[0]["item"]["title"], "screening ranks catalysts above recaps")

    rc, _ = quiet(stock_lookup.main, ["--manual", "999005", "戊公司", "--pct", "3.5", "--price", "8.8",
                                     "--source", "selftest", "--date", "2026-09-24"])
    lk = read_json(ddir / "lookup.json")
    check(rc == 0 and lk["stocks"]["999005"]["cap"] == "8.80 元 · 9/24 +3.50%"
          and lk["stocks"]["999005"]["excess"] == 4.72, "manual quote recorded (no float cap) with excess")

    print("4. daily finish")
    import daily
    from ta_common import dist_dir
    lq = daily.latest_quotes()
    check(lq.get("999001", {}).get("date") == "2026-09-24", "latest quotes merged from quotes.json + lookup.json")
    rc, out = quiet(daily.main, ["finish", "--date", "2026-09-24"])
    built = dist_dir() / "题材档案库.html"
    check(rc == 0 and built.exists() and (dist_dir() / "题材档案库_20260924.html").exists(), "finish validates and builds")
    check("12.43 元 · 流通 638 亿 · 9/24 -1.51%" in built.read_text(encoding="utf-8"), "finish refreshes quote lines")

    print("5. MCP client")
    import mcp_client
    os.environ["SELFTEST_MCP_TOKEN"] = "tok-123"
    os.environ.pop("SELFTEST_MCP_UNSET", None)
    for var in ("no_proxy", "NO_PROXY"):
        os.environ[var] = ",".join(filter(None, ["127.0.0.1,localhost", os.environ.get(var)]))
    srv = fake_mcp_server("tok-123")
    url = f"http://127.0.0.1:{srv.server_address[1]}/ds-mcp-servers/fake"
    cfg = str(tmp / "mcp.json")
    write_json(cfg, {"mcpServers": {
        "fake": {"type": "streamablehttp", "url": url, "headers": {"Authorization": "${SELFTEST_MCP_TOKEN}"}},
        "badtoken": {"type": "http", "url": url, "headers": {"Authorization": "wrong"}},
        "unset": {"type": "http", "url": url, "headers": {"Authorization": "${SELFTEST_MCP_UNSET}"}},
        "closed": {"type": "http", "url": "http://127.0.0.1:9/mcp"}}})
    catalog = tmp / "mcp_tools.json"
    rc, out = quiet(mcp_client.main, ["--config", cfg, "probe", "fake", "--out", str(catalog)])
    cat = read_json(catalog) if catalog.exists() else {}
    check(rc == 0 and [t["name"] for t in cat.get("fake", {}).get("tools", [])] == ["get_quote", "get_kline", "get_news"],
          "probe: handshake, SSE reply, paginated tools/list")
    check(cat.get("fake", {}).get("protocol") == "2025-03-26" and cat["fake"]["server"]["name"] == "fake-ifind",
          "probe: negotiated protocol and server info recorded")
    rc, out = quiet(mcp_client.main, ["--config", cfg, "call", "fake", "get_quote", '{"code": "999001.SH"}'])
    check(rc == 0 and '"close": 12.43' in out and "999001.SH" in out, "call: tool result printed")
    rc, out = quiet(mcp_client.main, ["--config", cfg, "call", "fake", "nope"])
    check(rc == 1 and "unknown tool" in out, "call: JSON-RPC error reported")
    rc, out = quiet(mcp_client.main, ["--config", cfg, "probe", "badtoken"])
    check(rc == 4 and "AUTH FAILED" in out, "probe: rejected token -> exit 4")
    rc, out = quiet(mcp_client.main, ["--config", cfg, "probe", "unset"])
    check(rc == 1 and "SELFTEST_MCP_UNSET" in out, "probe: missing environment variable named")
    rc, out = quiet(mcp_client.main, ["--config", cfg, "probe", "closed"])
    check(rc == 2 and "UNREACHABLE" in out, "probe: unreachable host -> exit 2")
    srv.shutdown()
    srv.server_close()

    if args.reference:
        print("6. round-trip against reference")
        ref = Path(args.reference)
        out_dir = tmp / "roundtrip"
        import import_html
        quiet(import_html.main, [str(ref), "--out", str(out_dir), "--quiet"])
        html = build_archive.render_page(load_cases(out_dir), build_archive.Opts(legacy=True))
        same = html.encode("utf-8") == ref.read_bytes()
        check(same, f"legacy rebuild of {ref.name} is byte-identical ({len(list(out_dir.glob('*.json')))} cases)")

    if FAILS:
        print(f"\n{len(FAILS)} FAILED (temp archive kept for inspection: {tmp})")
        return 1
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
