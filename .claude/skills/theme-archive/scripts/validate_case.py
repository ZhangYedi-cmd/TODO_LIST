#!/usr/bin/env python3
"""Validate case JSON files against the archive schema and house rules.

    python3 validate_case.py [CASE.json ...] [--all] [--strict]

With no file arguments, validates cases dated today (CST).  --all checks the
whole archive.  Exit code 1 when any ERROR is found (--strict: also on WARN).

ERROR = the page would render wrong or the case breaks a hard rule
(compliance, enums, fixed structure).  WARN = off the house style (lengths,
counts, numbers that disagree with market data).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import (  # noqa: E402
    ARCHIVE_LEVELS, DECISION_STEPS, DRIVERS, POSITION_STEP_TEXT, PRICING, RING_NAMES, ROLES, TONES,
    cases_dir, data_dir, load_cases, read_json, role_of_title, strip_tags, today_cn,
)

ADVICE = re.compile(
    # advisory phrasings only; descriptive market language (资金加仓、空头减仓、基金重仓股) is fine
    r"建议(买入|卖出|关注|配置|增持|减持|加仓|减仓|建仓|清仓|持有)|逢(低|高)(买入|布局|吸纳|加仓|减仓)|买入机会|"
    r"(择机|可以|可|适时|积极|适当|分批|宜|应当|应)(买入|卖出|介入|加仓|减仓|建仓|清仓)|"
    r"(设置|设好)?止(损|盈)(位|价|线)|满仓|半仓|轻仓|重仓(配置|参与|买入)|仓位建议|抄底|追涨|低吸|高抛|目标位|"
    r"看到\s*\d+(\.\d+)?\s*元")
ALLOWED_TAGS = {"strong", "b", "br", "em", "span"}
# (min, max) plain-text length; outside -> WARN.  Derived from the reference archive (p5..max).
LEN = {
    "title": (4, 22), "subtitle": (25, 130), "positionNote": (45, 95), "pricingDetail": (150, 1100),
    "verdict": (230, 900), "ringSummary": (30, 80), "grade.text": (8, 50),
    "fact.value": (60, 560), "ring.point": (10, 90), "assessment": (35, 360),
    "stock.logic": (4, 34), "stock.detail": (30, 260), "stock.risk": (6, 70), "stock.gene": (18, 120),
    "core.detail": (130, 420), "core.confirm": (15, 90), "ext.detail": (60, 240),
    "not.logic": (12, 200), "history": (30, 210), "dc.text": (45, 230),
    "scen.trigger": (15, 100), "scen.state": (25, 380), "scen.signal": (8, 160),
    "sig": (12, 80), "cal.what": (8, 60), "cal.why": (8, 60),
}


class Report:
    def __init__(self, cid: str):
        self.cid, self.errors, self.warns, self.md_fields = cid, [], [], []

    def err(self, m):
        self.errors.append(m)

    def warn(self, m):
        self.warns.append(m)


def check_len(r: Report, key: str, value: str, where: str) -> None:
    lo, hi = LEN[key]
    n = len(strip_tags(value or ""))
    if n < lo or n > hi:
        r.warn(f"{where}: length {n} outside house range {lo}-{hi}")


def check_html(r: Report, value: str, where: str, legacy: bool = False) -> None:
    if not isinstance(value, str):
        r.err(f"{where}: must be a string")
        return
    tags = re.findall(r"</?([a-zA-Z0-9]+)[^>]*>", value)
    bad = sorted({t for t in tags if t.lower() not in ALLOWED_TAGS})
    if bad:
        r.err(f"{where}: disallowed HTML tags {bad} (use <strong>/<b>/<br>)")
    for t in ("strong", "b", "em", "span"):
        if len(re.findall(rf"<{t}[\s>]", value)) != len(re.findall(rf"</{t}>", value)):
            (r.warn if legacy else r.err)(f"{where}: unbalanced <{t}>")
    if "TODO" in value:
        r.err(f"{where}: contains TODO placeholder")
    if "**" in value:
        r.md_fields.append(where)


def walk_strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from walk_strings(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, x in obj.items():
            yield from walk_strings(x, f"{path}.{k}" if path else k)


def validate(c: dict, known_ids: set[str], market: dict | None = None, legacy: bool = False) -> Report:
    r = Report(c.get("id", "?"))

    def L(key: str, value: str, where: str) -> None:
        if not legacy:  # imported reference cases define the ranges; don't re-judge them
            check_len(r, key, value, where)
    req = ["id", "date", "title", "subtitle", "grade", "driver", "pricing", "mainline", "archiveLevel",
           "positionNote", "pricingDetail", "facts", "timeline", "verdict", "rings", "ringSummary", "assessment",
           "stockTiers", "history", "coreLinks", "extendedLinks", "notInChain", "decisionChain", "scenarios",
           "signals", "calendar", "sources"]
    for k in req:
        if k not in c:
            r.err(f"missing field `{k}`")
    if r.errors:
        return r

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", c["id"]):
        r.err("id must be kebab-case ascii, e.g. `copper-record`")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", c["date"]):
        r.err("date must be YYYY-MM-DD")

    # ---- enums
    g = c["grade"]
    if g.get("tone") not in TONES:
        (r.warn if legacy else r.err)(f"grade.tone must be one of {list(TONES)}")
    elif not g.get("text", "").startswith(TONES[g["tone"]]):
        r.err(f"grade.text must start with {TONES[g['tone']]} for tone {g['tone']}")
    if " · " not in g.get("text", "") and not legacy:
        r.warn("grade.text should read '<emoji> <定性> · <矛盾点>'")
    for key, allowed in (("driver", DRIVERS), ("pricing", PRICING), ("archiveLevel", ARCHIVE_LEVELS)):
        if c[key] not in allowed:
            (r.warn if legacy else r.err)(f"{key} `{c[key]}` not in {allowed}")
    if c["archiveLevel"] == "正式档" and g.get("tone") == "fire" and c["pricing"] == "已定价":
        r.warn("🔥 with 已定价 is contradictory (已定价 is normally ⚠)")

    # ---- per-section structure
    if not 5 <= len(c["facts"]) <= 9:
        r.warn(f"facts: {len(c['facts'])} cards (house style 6-8)")
    if not any("盘面" in f.get("key", "") for f in c["facts"]):
        r.warn("facts: no 盘面验证 card")
    if not any(f.get("warn") for f in c["facts"]):
        r.warn("facts: no 争议点 card with warn=true")
    for i, f in enumerate(c["facts"]):
        L("fact.value", f.get("value", ""), f"facts[{i}]")
    if not c["timeline"]:
        r.err("timeline: at least one entry")
    if [x.get("name") for x in c["rings"]] != RING_NAMES:
        r.err(f"rings must be exactly {RING_NAMES} in order")
    for x in c["rings"]:
        if len(x.get("points", [])) != 2:
            r.warn(f"ring {x.get('name')}: {len(x.get('points', []))} points (house style 2)")
        if len(x.get("verdict", "")) > 8:
            r.warn(f"ring {x.get('name')}: verdict should be a 1-4 char 判词")
    if len(c["assessment"]) < 3:
        r.warn("assessment: expected 闭合度 / 边界 / 主线联动")
    elif not re.search(r"闭合度\s*(<strong>)?\s*\d+%", c["assessment"][0]):
        r.err("assessment[0] must state 闭合度 NN%")

    order = [role for role, _ in ROLES]
    last = -1
    n_stocks = 0
    for t in c["stockTiers"]:
        role = t.get("role") or role_of_title(t.get("title", ""))
        if role is None:
            r.err(f"stock tier `{t.get('title')}`: title must name a role {order}")
            continue
        if order.index(role) < last:
            r.warn(f"stock tiers out of order (expected {' > '.join(order)})")
        last = order.index(role)
        for s in t.get("stocks", []):
            n_stocks += 1
            where = f"{role}/{s.get('name')}"
            for k in ("name", "code", "logic"):
                if not s.get(k):
                    r.err(f"{where}: missing {k}")
            if s.get("code") and not re.fullmatch(r"\d{6}|—", s["code"]):
                r.err(f"{where}: code must be 6 digits or —")
            if not legacy:
                for k in ("tag", "detail", "risk"):
                    if not s.get(k):
                        r.err(f"{where}: missing {k}")
                if role in ("情绪小票", "情绪龙") and not s.get("gene"):
                    r.err(f"{where}: emotional tiers need a 题材基因 `gene`")
            L("stock.logic", s.get("logic", ""), where)
            if s.get("detail"):
                L("stock.detail", s["detail"], where)
            if s.get("gene"):
                L("stock.gene", s["gene"], where)
    if not legacy and not 3 <= n_stocks <= 13:
        r.warn(f"{n_stocks} stock cards (house style 5-11)")
    for s in c["coreLinks"]:
        where = f"核心/{s.get('name')}"
        if not legacy and s.get("logic", "").count("|") < 2:
            r.warn(f"{where}: logic should be '产业地位 | 弹性来源 | 约束条件'")
        for k in ("detail", "confirm", "risk"):
            if not s.get(k):
                r.err(f"{where}: missing {k}")
        if s.get("detail"):
            L("core.detail", s["detail"], where)
    for s in c["extendedLinks"]:
        for k in ("detail", "risk"):
            if not s.get(k):
                r.err(f"延伸/{s.get('name')}: missing {k}")
    if len(c["notInChain"]) < 2 and not legacy:
        r.warn("notInChain: list at least 2 false mappings (反向清单)")
    if not 3 <= len(c["history"]) <= 5:
        r.warn(f"history: {len(c['history'])} items (house style 3-4)")

    names = [s.get("name") for s in c["decisionChain"]]
    if names != DECISION_STEPS:
        r.err(f"decisionChain must be exactly {DECISION_STEPS}")
    else:
        pos = c["decisionChain"][6]["text"]
        if pos != POSITION_STEP_TEXT:
            r.err(f"decisionChain 仓位 must read exactly `{POSITION_STEP_TEXT}`")
    if not legacy and not 3 <= len(c["scenarios"]) <= 4:
        r.err(f"scenarios: {len(c['scenarios'])} branches (need 3-4 mutually exclusive)")
    for k in ("verify", "falsify"):
        n = len(c["signals"].get(k, []))
        if not 3 <= n <= 6:
            r.warn(f"signals.{k}: {n} items (house style 3-6)")
    if not 3 <= len(c["calendar"]) <= 5:
        r.warn(f"calendar: {len(c['calendar'])} items (house style 3-5)")
    for rel in c.get("relatedCases") or []:
        if rel not in known_ids:
            r.warn(f"relatedCases: unknown case `{rel}`")

    # ---- lengths of single fields
    for key in ("title", "subtitle", "positionNote", "pricingDetail", "verdict", "ringSummary"):
        L(key, c[key], key)
    L("grade.text", g.get("text", ""), "grade.text")
    for x in c["rings"]:
        for i, p in enumerate(x.get("points", [])):
            L("ring.point", p, f"ring {x.get('name')}[{i}]")
    for i, a in enumerate(c["assessment"]):
        L("assessment", a, f"assessment[{i}]")
    for i, h in enumerate(c["history"]):
        L("history", h, f"history[{i}]")
    for s in c["decisionChain"]:
        if s.get("name") != "仓位":
            L("dc.text", s.get("text", ""), f"decisionChain/{s.get('name')}")
    for i, sc in enumerate(c["scenarios"]):
        for k in ("trigger", "state", "signal"):
            L(f"scen.{k}", sc.get(k, ""), f"scenarios[{i}].{k}")
    for k in ("verify", "falsify"):
        for i, v in enumerate(c["signals"].get(k, [])):
            L("sig", v, f"signals.{k}[{i}]")
    for i, t in enumerate(c["calendar"]):
        L("cal.what", t.get("what", ""), f"calendar[{i}].what")
        L("cal.why", t.get("why", ""), f"calendar[{i}].why")
    for s in c["coreLinks"]:
        if s.get("confirm"):
            L("core.confirm", s["confirm"], f"核心/{s.get('name')}")
    for s in c["extendedLinks"]:
        if s.get("detail"):
            L("ext.detail", s["detail"], f"延伸/{s.get('name')}")
    for s in c["notInChain"]:
        L("not.logic", s.get("logic", ""), f"不在链上/{s.get('name')}")
    for t in c["stockTiers"]:
        for s in t.get("stocks", []):
            if s.get("risk"):
                L("stock.risk", s["risk"], f"{t.get('title')}/{s.get('name')}")

    # ---- every string: html + compliance
    for path, value in walk_strings(c):
        check_html(r, value, path, legacy)
        if path.startswith("decisionChain[6]") or path in ("id",):
            continue
        m = ADVICE.search(strip_tags(value))
        if m:
            r.err(f"{path}: investment-advice wording `{m.group(0)}` (合规：只写客观条件)")

    if r.md_fields:
        r.warn(f"markdown ** in {len(r.md_fields)} field(s) (rendered as <strong>; prefer <strong>)")

    # ---- numbers vs market data
    if market:
        text = " ".join(v for _, v in walk_strings(c))
        plain = strip_tags(text)
        for code, q in market.items():
            name, pct = q.get("name"), q.get("pct")
            if not name or pct is None:
                continue
            for m in re.finditer(re.escape(name) + r"[^，。；、%]{0,14}?([+-]\d+(?:\.\d+)?)%", plain):
                try:
                    v = float(m.group(1))
                except ValueError:
                    continue
                if abs(v - pct) > 0.02 and abs(v) < 21 and abs(pct) < 21:
                    ctx = m.group(0)
                    date_hint = re.search(r"\d{1,2}/\d{1,2}", plain[max(0, m.start() - 12):m.end()])
                    if date_hint is None or date_hint.group(0) == q.get("md"):
                        r.warn(f"number check: `{ctx}` but {q.get('trade_date')} close was {pct:+.2f}%")
                    break
    return r


def market_for(day: str) -> dict:
    ddir = data_dir(day)
    out = {}
    if (ddir / "quotes.json").exists():
        qs = read_json(ddir / "quotes.json")
        for code, q in qs["quotes"].items():
            out[code] = {"name": q.get("name"), "pct": q.get("pct"), "trade_date": qs.get("trade_date")}
    if (ddir / "lookup.json").exists():
        lk = read_json(ddir / "lookup.json")
        for code, q in lk.get("stocks", {}).items():
            out[code] = {"name": q.get("name"), "pct": q.get("pct"), "trade_date": q.get("trade_date")}
    for q in out.values():
        if q.get("trade_date"):
            y, m, d = q["trade_date"].split("-")
            q["md"] = f"{int(m)}/{int(d)}"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true", help="validate every case in the archive")
    ap.add_argument("--strict", action="store_true", help="fail on warnings too")
    ap.add_argument("--legacy", action="store_true", help="relax rules for imported legacy cases")
    ap.add_argument("--quiet", action="store_true", help="only print cases with errors")
    args = ap.parse_args(argv)

    archive = load_cases()
    known = {c["id"] for c in archive}
    if args.files:
        cases = [read_json(f) for f in args.files]
    elif args.all:
        cases = archive
    else:
        today = today_cn()
        cases = [c for c in archive if c.get("date") == today]
        if not cases:
            print(f"no cases dated {today} in {cases_dir()}")
            return 0
    known |= {c.get("id") for c in cases}
    n_err = n_warn = 0
    for c in cases:
        legacy = args.legacy or c.get("legacy", False)
        rep = validate(c, known, market_for(c.get("date", today_cn())), legacy=legacy)
        n_err += len(rep.errors)
        n_warn += len(rep.warns)
        if args.quiet and not rep.errors:
            continue
        status = "OK" if not rep.errors and not rep.warns else ("FAIL" if rep.errors else "WARN")
        print(f"[{status}] {rep.cid}: {len(rep.errors)} errors, {len(rep.warns)} warnings")
        for m in rep.errors:
            print(f"   ERROR {m}")
        for m in rep.warns:
            print(f"   warn  {m}")
    print(f"{len(cases)} case(s): {n_err} errors, {n_warn} warnings")
    return 1 if n_err or (args.strict and n_warn) else 0


if __name__ == "__main__":
    raise SystemExit(main())
