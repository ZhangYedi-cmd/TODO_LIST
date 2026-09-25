#!/usr/bin/env python3
"""Import an existing 题材档案库 HTML file into case JSON files.

    python3 import_html.py <archive.html> [--out DIR] [--extract-assets]

Every rich-text field keeps its raw inner HTML, so `build_archive.py` can
re-render the page byte for byte.  Use it to seed the archive from a report
you already have, or to migrate an archive produced elsewhere.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from htmldom import Doc  # noqa: E402
from ta_common import ASSETS_DIR, PREFIX, cases_dir, role_of_title, write_json  # noqa: E402

WARN: list[str] = []


def warn(msg: str) -> None:
    WARN.append(msg)


def strip_prefix(value: str, prefix: str, where: str) -> str:
    if value.startswith(prefix):
        return value[len(prefix):]
    warn(f"{where}: missing prefix {prefix!r}: {value[:40]!r}")
    return value


def unwrap_b(value: str, where: str) -> str:
    m = re.fullmatch(r"<b>(.*)</b>", value, re.S)
    if not m:
        warn(f"{where}: expected <b>…</b>: {value[:40]!r}")
        return value
    return m.group(1)


def parse_card(doc: Doc, card, where: str) -> dict:
    row = card.find("div", "row")
    out = {
        "name": doc.inner(row.find("b")),
        "code": doc.inner(row.find("span", "code")),
    }
    for fld in ("tag", "cap"):
        n = row.find("span", fld)
        if n is not None:
            out[fld] = doc.inner(n)
    out["logic"] = doc.inner(card.find("div", "logic"))
    for fld in ("detail", "gene", "confirm", "risk"):
        n = card.find("div", fld, recursive=False)
        if n is not None:
            v = doc.inner(n)
            if fld in PREFIX:
                v = strip_prefix(v, PREFIX[fld], f"{where}/{out['name']}/{fld}")
            out[fld] = v
    return out


def parse_case(doc: Doc, sec) -> dict:
    cid = sec.attrs["id"].removeprefix("case-")
    w = f"case {cid}"
    wrap = sec.find("div", "wrap", recursive=False)
    c: dict = {"schemaVersion": 1, "id": cid, "legacy": True}
    c["date"] = doc.text(wrap.find("div", "datechip")).split("·")[-1].strip()
    c["title"] = doc.inner(wrap.find("h1"))
    c["subtitle"] = doc.inner(wrap.find("div", "sub"))

    badges = wrap.find("div", "badges").kids("span")
    g = badges[0]
    tone = [x for x in g.classes if x != "badge"]
    c["grade"] = {"tone": tone[0] if tone else "", "text": doc.inner(g)}
    neutral = [doc.inner(b) for b in badges[1:] if b.has_class("neutral")]
    c["driver"] = neutral[0]
    c["pricing"] = neutral[1].removeprefix("定价状态：")
    c["mainline"] = neutral[2].removeprefix("主线：")
    down = [b for b in badges if b.has_class("gradedown")]
    c["archiveLevel"] = "降档" if down else "正式档"
    if down:
        c["downgradeBadge"] = doc.inner(down[0])

    rel = [n for n in wrap.kids("div", "pos")]
    if rel:
        c["relatedCases"] = [doc.inner(t) for t in rel[0].find_all("span", "tag")]
    c["positionNote"] = doc.inner(wrap.find("div", "posnote", recursive=False))
    det = wrap.find("details", "more", recursive=False)
    if det is not None:
        summary = doc.text(det.find("summary"))
        m = re.search(r"（(\d+) 字）", summary)
        pos = det.find("div", "pos")
        body = doc.inner(pos)
        c["pricingDetail"] = strip_prefix(body, "<b>定价状态备注：</b>", f"{w}/pricingDetail")
        if m:
            c["pricingDetailChars"] = int(m.group(1))

    # sections are identified by their h2 title
    sections: dict[str, object] = {}
    kids = wrap.children
    for i, n in enumerate(kids):
        if n.tag == "h2":
            title = doc.text(n).lstrip(">").strip()
            sections[title] = i

    def after(title: str, k: int = 1):
        i = sections.get(title)
        return None if i is None else kids[i + k]

    grid = after("核心事实")
    c["facts"] = []
    for f in grid.kids("div", "fact"):
        c["facts"].append({
            "key": doc.inner(f.find("b", "k")),
            "value": doc.inner(f.find("div", "v")),
            "warn": f.has_class("warn"),
        })

    c["timeline"] = []
    for u in after("主线更新（多段催化时间线）").kids("div", "u"):
        c["timeline"].append({
            "when": doc.inner(u.find("div", "w")),
            "what": doc.inner(u.find("div", "x")),
            "why": strip_prefix(doc.inner(u.find("div", "y")), PREFIX["why"], f"{w}/timeline"),
        })

    c["verdict"] = doc.inner(after("逻辑推演"))

    rings = after("产业链逻辑链条")
    c["rings"] = [{
        "name": doc.inner(r.find("span", "k")),
        "verdict": doc.inner(r.find("span", "vt")),
        "points": [doc.inner(li) for li in r.find("ul").kids("li")],
    } for r in rings.kids("div", "ring")]
    c["ringSummary"] = strip_prefix(doc.inner(after("产业链逻辑链条", 2)), PREFIX["summary"], f"{w}/sum")
    c["assessment"] = [doc.inner(li) for li in after("产业链逻辑链条", 3).kids("li")]

    # ---- tiers
    c["stockTiers"], c["history"], c["coreLinks"], c["extendedLinks"], c["notInChain"] = [], [], [], [], []
    i = sections["环节 × 标的 × 映射逻辑"] + 1
    while i < len(kids) and kids[i].tag != "h2":
        tier = kids[i]
        i += 1
        if not tier.has_class("tier"):
            continue
        heads = tier.kids("div", "t")
        first = doc.text(heads[0])
        if first.startswith("📜"):
            c["history"] = [doc.inner(li) for li in tier.find("ul").kids("li")]
            continue
        if first.startswith("⛓️") or first.startswith("🔗") or first.startswith("🚫"):
            key = "coreLinks" if first.startswith("⛓️") else "extendedLinks" if first.startswith("🔗") else "notInChain"
            expect = {"coreLinks": "⛓️ 核心环节 · 传导链最短", "extendedLinks": "🔗 延伸环节 · 传导链较远",
                      "notInChain": "🚫 不在传导链上"}[key]
            if doc.inner(heads[0]) != expect:
                warn(f"{w}: unexpected tier title {doc.inner(heads[0])!r}")
            cols = tier.find("div", "cols")
            c[key] = [parse_card(doc, card, w) for card in cols.kids("div", "card")]
            continue
        # stock tiers: several (t, cols) pairs inside one .tier
        for h in heads:
            raw = doc.inner(h)
            m = re.fullmatch(r'(.*?) <span style="font-size:12px;color:var\(--dim\);font-weight:400;'
                             r'margin-left:8px">· (.*?)</span>', raw, re.S)
            if not m:
                warn(f"{w}: stock tier head not recognised {raw[:60]!r}")
                continue
            title, drv = m.group(1), m.group(2)
            if role_of_title(title) is None:
                warn(f"{w}: unknown role in tier title {title!r}")
            idx = tier.children.index(h)
            cols = tier.children[idx + 1]
            c["stockTiers"].append({
                "title": title,
                "driver": drv,
                "stocks": [parse_card(doc, card, w) for card in cols.kids("div", "card")],
            })

    # ---- decision chain
    dc = after("合规决策链 · 八要素", 2)
    hint = doc.inner(after("合规决策链 · 八要素", 1))
    if hint != "固定八步。第 04 步只给客观确认条件、第 07 步合规剥离——全文不含价位/仓位/买卖建议。":
        warn(f"{w}: dchint differs")
    c["decisionChain"] = []
    for s in dc.kids("div", "dcstep"):
        sn = s.find("div", "sn")
        style = [x for x in s.classes if x != "dcstep"]
        c["decisionChain"].append({
            "name": doc.inner(sn.find("span", "sname")),
            "text": doc.inner(s.find("div", "st")),
            "style": style[0] if style else "",
        })
        num = doc.inner(sn).split("<", 1)[0]
        if num != f"{len(c['decisionChain']):02d}":
            warn(f"{w}: decision step numbering {num}")

    c["scenarios"] = []
    if "情景推演" in sections:
        hint = doc.inner(after("情景推演", 1))
        if hint != "每个分支为可观察的条件树——触发条件兑现后的逻辑状态与验证信号，互斥且可证伪。不含操作建议。":
            warn(f"{w}: scenario hint differs")
        for sc in after("情景推演", 2).kids("div", "sc"):
            def part(cls, label):
                v = doc.inner(sc.find("div", cls))
                return unwrap_b(strip_prefix(v, label, f"{w}/scenario"), f"{w}/scenario")
            c["scenarios"].append({
                "branch": strip_prefix(doc.inner(sc.find("div", "br")), PREFIX["branch"], f"{w}/scenario"),
                "trigger": part("tg", "触发："),
                "state": part("ls", "逻辑状态："),
                "signal": part("fs", "观察信号："),
            })

    sig = after("信号对照台")
    boxes = sig.kids("div", "sigbox")
    c["signals"] = {
        "verify": [unwrap_b(doc.inner(li), f"{w}/signals") for li in boxes[0].find("ol").kids("li")],
        "falsify": [unwrap_b(doc.inner(li), f"{w}/signals") for li in boxes[1].find("ol").kids("li")],
    }

    c["calendar"] = [{
        "when": doc.inner(t.find("div", "w")),
        "what": doc.inner(t.find("div", "wh")),
        "why": doc.inner(t.find("div", "wy")),
    } for t in after("跟踪日历").kids("div", "tkc")]

    src = wrap.find("div", "src", recursive=False)
    c["sources"] = strip_prefix(doc.inner(src), "数据来源：", f"{w}/sources")
    footer = doc.inner(wrap.find("footer", recursive=False))
    if footer != f"{c['title']} · 题材分析框架 · 客观产业研究，不含投资建议":
        warn(f"{w}: footer differs: {footer!r}")
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("--out", default=None, help="output dir for case JSON (default: archive cases dir)")
    ap.add_argument("--extract-assets", action="store_true", help="also write assets/archive.css and router.js.tpl")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    src = Path(args.html).read_text(encoding="utf-8")
    doc = Doc(src)
    out = Path(args.out) if args.out else cases_dir()

    if args.extract_assets:
        css = re.search(r"<style>\n(.*?)\n</style>", src, re.S).group(1)
        js = re.search(r"<script>\n(.*?)\n</script>", src, re.S).group(1)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        (ASSETS_DIR / "archive.css").write_text(css + "\n", encoding="utf-8")
        (ASSETS_DIR / "router.js.tpl").write_text(js + "\n", encoding="utf-8")

    sections = doc.root.find_all("section", "case")
    for sec in sections:
        case = parse_case(doc, sec)
        write_json(out / f"{case['id']}.json", case)
    if not args.quiet:
        print(f"imported {len(sections)} cases -> {out}")
        for m in WARN:
            print("WARN", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
