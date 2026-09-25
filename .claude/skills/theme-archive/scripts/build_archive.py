#!/usr/bin/env python3
"""Render every case JSON into the single-file 题材档案库 HTML.

    python3 build_archive.py [--cases DIR] [--out FILE] [--quotes FILE] [--legacy]

The markup mirrors the reference archive byte for byte (same CSS, same DOM,
same classes, same whitespace), so the output looks exactly like it.

What the build does on top of plain rendering:
  * sorts cases (newest date first, then id) and computes the index stats;
  * links every case to the other cases on the same 主线 (relatedCases), so
    older cases also point at newer ones;
  * refreshes each stock card's quote line (`cap`) from --quotes when given;
  * turns leftover **markdown bold** into <strong>.
--legacy turns the last three off, which reproduces a legacy archive exactly
(used by the round-trip self-test).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import (  # noqa: E402
    ASSETS_DIR, DECISION_STYLE, PREFIX, PRICING, ROLE_DEFAULT_TITLE, TONES, cases_dir, dist_dir,
    load_cases, md_bold, read_json,
)

PAGE_TITLE = "题材档案库 · 题材档案库"
DCHINT = "固定八步。第 04 步只给客观确认条件、第 07 步合规剥离——全文不含价位/仓位/买卖建议。"
SCEN_HINT = "每个分支为可观察的条件树——触发条件兑现后的逻辑状态与验证信号，互斥且可证伪。不含操作建议。"
TIER_SPAN = '<span style="font-size:12px;color:var(--dim);font-weight:400;margin-left:8px">· {}</span>'
GRID_PAD = " " * 6  # the reference file carries this whitespace-only line
HIST_UL_STYLE = "background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 16px 12px 14px"


class Opts:
    def __init__(self, legacy: bool = False, quotes: dict | None = None):
        self.legacy = legacy
        self.quotes = quotes or {}

    def rich(self, s: str) -> str:
        return s if self.legacy else md_bold(s)


def normalize(c: dict) -> dict:
    """Fix legacy data that breaks the index: off-enum pricing and missing grade tone."""
    c = dict(c)
    p = c.get("pricing", "")
    if p not in PRICING:
        c["pricing"] = next((x for x in ("部分定价", "未定价", "已定价") if x in p), p)
    g = dict(c.get("grade", {}))
    if g.get("tone") not in TONES:
        text = g.get("text", "")
        g["tone"] = next((t for t, e in TONES.items() if text.startswith(e)), "bolt")
    c["grade"] = g
    return c


def attr(s: str) -> str:
    return s.replace('"', "&quot;")


def search_text(*parts: str) -> str:
    return attr(" ".join(p for p in parts).lower())


# ------------------------------------------------------------------ quotes
def fmt_cap(q: dict) -> str:
    """{'price':12.79,'float_cap':6.38e10,'pct':2.81,'date':'2026-09-16'} -> '12.79 元 · 流通 638 亿 · 9/16 +2.81%'"""
    fc = q["float_cap"] / 1e8
    cap = f"{fc / 1e4:.2f} 万亿" if fc >= 1e4 else f"{fc:.0f} 亿"
    y, m, d = q["date"].split("-")
    return f"{q['price']:.2f} 元 · 流通 {cap} · {int(m)}/{int(d)} {q['pct']:+.2f}%"


def cap_for(stock: dict, opts: Opts) -> str | None:
    q = opts.quotes.get(stock.get("code", ""))
    if q and q.get("price") and q.get("float_cap"):
        return fmt_cap(q)
    return stock.get("cap")


# ------------------------------------------------------------------ cards
def card(stock: dict, opts: Opts, with_cap: bool) -> str:
    row = f'<b>{stock["name"]}</b><span class="code">{stock.get("code") or "—"}</span>'
    if stock.get("tag"):
        row += f'<span class="tag">{stock["tag"]}</span>'
    cap = cap_for(stock, opts) if with_cap else stock.get("cap")
    if cap:
        row += f'<span class="cap">{cap}</span>'

    def line(cls: str) -> str:
        v = stock.get(cls)
        if not v:
            return ""
        prefix = PREFIX.get(cls, "")
        if prefix and not v.startswith(prefix):
            v = prefix + v
        return f'<div class="{cls}">{opts.rich(v)}</div>'

    return (
        "\n  <div class=\"card\">"
        f"\n    <div class=\"row\">{row}</div>"
        f"\n    <div class=\"logic\">{opts.rich(stock.get('logic', ''))}</div>"
        f"\n    {line('detail')}"
        f"\n    {line('gene')}"
        f"\n    {line('confirm')}"
        f"\n    {line('risk')}"
        "\n  </div>"
    )


def stock_tiers(c: dict, opts: Opts) -> str:
    tiers = [t for t in c.get("stockTiers", []) if t.get("stocks")]
    if not tiers:
        return ""
    out = '<div class="tier">'
    for t in tiers:
        title = t.get("title") or ROLE_DEFAULT_TITLE.get(t.get("role", ""), t.get("role", ""))
        out += f'<div class="t">{title} {TIER_SPAN.format(t.get("driver") or c["driver"])}</div>'
        out += '<div class="cols">' + "".join(card(s, opts, True) for s in t["stocks"]) + "</div>"
    return out + "</div>"


def link_tier(title: str, items: list, opts: Opts) -> str:
    if not items:
        return ""
    cards = "".join(card(s, opts, False) for s in items)
    return f'<div class="tier"><div class="t">{title}</div><div class="cols">{cards}</div></div>'


def history_tier(c: dict, opts: Opts) -> str:
    if not c.get("history"):
        return ""
    lis = "".join(f"<li>{opts.rich(x)}</li>" for x in c["history"])
    return (f'<div class="tier" style="margin-top:16px"><div class="t">📜 历史妖股记忆 / 同类行情参照</div>'
            f'<ul class="hist" style="{HIST_UL_STYLE}">{lis}</ul></div>')


# ------------------------------------------------------------------ case page
def related_for(c: dict, all_cases: list[dict], opts: Opts) -> list[str]:
    rel = list(c.get("relatedCases") or [])
    if opts.legacy:
        return rel
    known = {x["id"] for x in all_cases}
    rel = [r for r in rel if r in known and r != c["id"]]
    same = sorted(x["id"] for x in all_cases if x.get("mainline") == c.get("mainline") and x["id"] != c["id"])
    return rel + [r for r in same if r not in rel]


def render_case(c: dict, all_cases: list[dict], opts: Opts) -> str:
    R = opts.rich
    tone = c["grade"].get("tone", "")
    down = c.get("archiveLevel") == "降档"
    down_badge = f'<span class="badge gradedown">{c.get("downgradeBadge") or "⚑ 降档入库 · 只配情绪波段，不格局中线"}</span>' if down else ""

    rel = related_for(c, all_cases, opts)
    rel_html = ""
    if rel:
        tags = "".join(f'<span class="tag" style="margin-right:4px">{r}</span>' for r in rel)
        rel_html = f'<div class="pos" style="border-left-color:var(--faint)"><b>主线联动档案：</b>{tags}</div>'

    detail = c.get("pricingDetail", "")
    details_html = ""
    if detail:
        detail = R(detail)
        n = c.get("pricingDetailChars") if opts.legacy else len(detail)
        details_html = (f'<details class="more"><summary>展开定价状态详版（{n} 字）</summary>'
                        f'<div class="pos"><b>定价状态备注：</b>{detail}</div></details>')

    facts = "".join(
        f'<div class="card fact{" warn" if f.get("warn") else ""}"><b class="k">{f["key"]}</b>'
        f'<div class="v">{R(f["value"])}</div></div>' for f in c["facts"])
    updates = "".join(
        f'<div class="u"><div class="w">{u["when"]}</div><div><div class="x">{R(u["what"])}</div>'
        f'<div class="y">{PREFIX["why"]}{R(u["why"])}</div></div></div>' for u in c["timeline"])
    rings = "".join(
        f'<div class="ring"><span class="k">{r["name"]}</span><span class="vt">{r["verdict"]}</span><ul>'
        + "".join(f"<li>{R(p)}</li>" for p in r["points"]) + "</ul></div>" for r in c["rings"])
    assess = "".join(f"<li>{R(a)}</li>" for a in c.get("assessment", []))

    steps = []
    for i, s in enumerate(c["decisionChain"], 1):
        style = s.get("style", DECISION_STYLE.get(s["name"], "")) if opts.legacy else s.get("style") or DECISION_STYLE.get(s["name"], "")
        cls = f"dcstep {style}" if style else "dcstep"
        steps.append(f'<div class="{cls}"><div class="sn">{i:02d}<span class="sname">{s["name"]}</span></div>'
                     f'<div class="st">{R(s["text"])}</div></div>')

    if c.get("scenarios"):
        scs = "".join(
            f'<div class="sc"><div class="br">{PREFIX["branch"]}{s["branch"]}</div>'
            f'<div class="tg">触发：<b>{R(s["trigger"])}</b></div>'
            f'<div class="ls">逻辑状态：<b>{R(s["state"])}</b></div>'
            f'<div class="fs">观察信号：<b>{R(s["signal"])}</b></div></div>' for s in c["scenarios"])
        scen = (f'    <h2><span class="p">&gt;</span>情景推演</h2>\n'
                f'    <div style="font-size:12px;color:var(--dim);margin-bottom:8px">{SCEN_HINT}</div>\n'
                f'    <div class="scen">{scs}</div>')
    else:
        scen = "    "

    ver = "".join(f"<li><b>{R(x)}</b></li>" for x in c["signals"]["verify"])
    fal = "".join(f"<li><b>{R(x)}</b></li>" for x in c["signals"]["falsify"])
    cal = "".join(
        f'<div class="tkc"><div class="w">{t["when"]}</div><div class="wh">{R(t["what"])}</div>'
        f'<div class="wy">{R(t["why"])}</div></div>' for t in c["calendar"])

    search = search_text(c["title"], c["subtitle"], c["driver"], c["grade"]["text"])
    return f"""<section class="case" id="case-{c['id']}" data-search="{search}">
  <header><div class="wrap">
  <div class="hrow">
    <div class="hleft">
      <a href="#/" class="back">← 档案库</a>
      <div class="brand"><b>题材</b>产业链研究<span>A股题材研究系统</span></div>
    </div>
    <div class="clock">{c['date']} <span class="live">ARCHIVE</span></div>
  </div></div></header>
  <div class="wrap">
    <div class="datechip"><a href="#/" class="crumb">档案库</a> / 概念解析 · {c['date']}</div>
    <h1>{c['title']}</h1>
    <div class="sub">{c['subtitle']}</div>
    <div class="badges">
      <span class="badge {tone}">{c['grade']['text']}</span>
      <span class="badge neutral">{c['driver']}</span>
      <span class="badge neutral">定价状态：{c['pricing']}</span>
      <span class="badge neutral">主线：{c['mainline']}</span>
      {down_badge}
    </div>
    {rel_html}
    <div class="posnote">{c['positionNote']}</div>
    {details_html}

    <h2><span class="p">&gt;</span>核心事实</h2>
    <div class="grid">{facts}</div>

    <h2><span class="p">&gt;</span>主线更新（多段催化时间线）</h2>
    <div class="updates">{updates}</div>

    <h2><span class="p">&gt;</span>逻辑推演</h2>
    <div class="verdict">{R(c['verdict'])}</div>

    <h2><span class="p">&gt;</span>产业链逻辑链条</h2>
    <div class="rings">{rings}</div>
    <div class="sum">{PREFIX['summary']}{R(c['ringSummary'])}</div>
    <ul class="assess">{assess}</ul>

    <h2><span class="p">&gt;</span>环节 × 标的 × 映射逻辑</h2>
    {stock_tiers(c, opts)}
    {history_tier(c, opts)}
    {link_tier('⛓️ 核心环节 · 传导链最短', c.get('coreLinks', []), opts)}
    {link_tier('🔗 延伸环节 · 传导链较远', c.get('extendedLinks', []), opts)}
    {link_tier('🚫 不在传导链上', c.get('notInChain', []), opts)}

    <h2><span class="p">&gt;</span>合规决策链 · 八要素</h2>
    <div class="dchint">{DCHINT}</div>
    <div class="dc">{''.join(steps)}</div>

{scen}

    <h2><span class="p">&gt;</span>信号对照台</h2>
    <div class="sig">
    <div class="sigbox v"><h3>✅ 验证信号</h3><div class="hint">出现 → 逻辑成立度提升</div><ol>{ver}</ol></div>
    <div class="sigbox f"><h3>❌ 证伪信号</h3><div class="hint">出现 → 逻辑成立度下降</div><ol>{fal}</ol></div>
    </div>

    <h2><span class="p">&gt;</span>跟踪日历</h2>
    <div class="tk">{cal}</div>

    <div class="src">数据来源：{c['sources']}</div>
    <footer>{c['title']} · 题材分析框架 · 客观产业研究，不含投资建议</footer>
  </div>
</section>"""


# ------------------------------------------------------------------ index page
def index_names(c: dict) -> list[str]:
    names: list[str] = []
    for s in [s for t in c.get("stockTiers", []) for s in t.get("stocks", [])] + c.get("coreLinks", []):
        if s["name"] not in names:
            names.append(s["name"])
    return names[:5]


def stock_count(c: dict) -> int:
    return sum(len(t.get("stocks", [])) for t in c.get("stockTiers", []))


def covered_count(c: dict) -> int:
    return stock_count(c) + len(c.get("coreLinks", [])) + len(c.get("extendedLinks", []))


def render_card(c: dict) -> str:
    names = index_names(c)
    down = c.get("archiveLevel") == "降档"
    search = search_text(c["title"], c["subtitle"], c["driver"], c["mainline"], c["pricing"], " ".join(names))
    nm = "".join(f'<span class="nm">{n}</span>' for n in names)
    return f"""<a class="card-c" href="#{c['id']}" data-search="{search}" data-grade="{c.get('archiveLevel', '正式档')}" data-pricing="{c['pricing']}">
  <div class="cTop">
    <span class="cdate">{c['date']}</span>
    <span class="crate {c['grade'].get('tone', '')}">{c['grade']['text']} {c['driver']}</span>
  </div>
  <div class="ctitle">{c['title']}</div>
  <div class="csub">{c['subtitle']}</div>
  <div class="cpos">{c['positionNote']}</div>
  <div class="cmeta">
    <span class="chip line">{c['mainline']}</span>
    {'<span class="chip down">⚑ 降档</span>' if down else ''}
    <span class="chip pri">{c['pricing']}</span>
    <span class="chip">标的 {stock_count(c)}</span>
    {nm}
  </div>
  <div class="cgo">打开档案 →</div>
</a>"""


def render_page(cases: list[dict], opts: Opts) -> str:
    if not opts.legacy:
        cases = [normalize(c) for c in cases]
    cases = sorted(cases, key=lambda c: c["id"])
    cases = sorted(cases, key=lambda c: c["date"], reverse=True)
    css = (ASSETS_DIR / "archive.css").read_text(encoding="utf-8").rstrip("\n")
    js = (ASSETS_DIR / "router.js.tpl").read_text(encoding="utf-8").rstrip("\n")
    tones = [c["grade"].get("tone", "") for c in cases]
    stats = {
        "total": len(cases),
        "fire": tones.count("fire"),
        "bolt": tones.count("bolt"),
        "warn": tones.count("warn"),
        "down": sum(1 for c in cases if c.get("archiveLevel") == "降档"),
        "covered": sum(covered_count(c) for c in cases),
    }
    dates = [c["date"] for c in cases]
    span = f"{max(dates)} 至 {min(dates)}" if dates else ""
    cards = "\n".join(render_card(c) for c in cases)
    sections = "\n\n".join(render_case(c, cases, opts) for c in cases)
    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{PAGE_TITLE}</title>
<style>
{css}
</style></head><body>

<!-- ================= 目录页（默认视图） ================= -->
<div id="page-index">
  <div class="head"><div class="wrap">
    <h1><b>题材</b>档案库</h1>
    <div class="st">题材档案库 · 自包含单文件 · 离线可看</div>
  </div></div>

  <div class="wrap">
    <div class="stats">
      <div class="stat"><div class="v">{stats['total']}</div><div class="k">档案总数</div></div>
      <div class="stat f"><div class="v">{stats['fire']}</div><div class="k">🔥 已启动</div></div>
      <div class="stat b"><div class="v">{stats['bolt']}</div><div class="k">⚡ 未充分定价</div></div>
      <div class="stat w"><div class="v">{stats['warn']}</div><div class="k">⚠ 风险信号</div></div>
      <div class="stat"><div class="v" style="color:#94a3b8">{stats['down']}</div><div class="k">⚑ 降档入库</div></div>
      <div class="stat"><div class="v">{stats['covered']}</div><div class="k">覆盖标的</div></div>
    </div>

    <div class="bar">
      <input id="q" type="text" placeholder="搜索题材 / 标的 / 关键词…">
      <button class="fbtn on" data-f="all">全部</button>
      <button class="fbtn" data-f="未定价">未定价</button>
      <button class="fbtn" data-f="部分定价">部分定价</button>
      <button class="fbtn" data-f="已定价">已定价</button>
    </div>

    <div class="grid-c" id="grid">
{GRID_PAD}
{cards}
    </div>
    <div class="empty" id="empty">— 无匹配档案 —</div>

    <footer style="margin-top:30px">题材档案库 · 单文件可分享版 · 共 {stats['total']} 份 · 生成于 {span}</footer>
  </div>
</div>

<!-- ================= 所有档案详情 ================= -->

{sections}

<!-- ==================== 路由逻辑（hash SPA） ==================== -->
<script>
{js}
</script>
</body></html>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=None, help="directory of case JSON (default: archive cases dir)")
    ap.add_argument("--out", default=None, help="output HTML (default: <archive>/dist/题材档案库.html)")
    ap.add_argument("--quotes", default=None, help="quotes JSON {code: {price, float_cap, pct, date}} to refresh cap lines")
    ap.add_argument("--legacy", action="store_true", help="render stored values verbatim (round-trip mode)")
    args = ap.parse_args(argv)

    cases = load_cases(Path(args.cases) if args.cases else cases_dir())
    if not cases:
        print("no cases found", file=sys.stderr)
        return 1
    quotes = {}
    if args.quotes:
        raw = read_json(args.quotes)
        quotes = raw.get("quotes", raw)
    out = Path(args.out) if args.out else dist_dir() / "题材档案库.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_page(cases, Opts(legacy=args.legacy, quotes=quotes)), encoding="utf-8")
    print(f"built {out} ({len(cases)} cases, {out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
