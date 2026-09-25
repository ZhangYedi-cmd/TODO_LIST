#!/usr/bin/env python3
"""Scaffold a new case JSON with every section and TODO hints.

    python3 new_case.py <id> --title 标题 [--date YYYY-MM-DD] [--mainline 主线] [--driver 产业周期] [--downgrade]

--downgrade scaffolds a 降档 case (methodology §1.1): tone warn, 题材催化级,
the ⚑ badge, and a 核心环节 card for「（本档无合格主攻标的）」 if nothing qualifies.

Writes cases/<id>.json (refuses to overwrite).  Replace every "TODO…" string;
validate_case.py fails while any remain.  Field meanings: references/case-schema.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import (  # noqa: E402
    DECISION_STEPS, DECISION_STYLE, DOWNGRADE_BADGE, POSITION_STEP_TEXT, cases_dir, today_cn, write_json,
)


def stock(role: str) -> dict:
    s = {"name": "TODO 简称", "code": "TODO 6位代码", "tag": "TODO 一句话定位(≤20字)", "cap": "",
         "logic": "TODO 映射逻辑(≤18字，可带当日涨跌)", "detail": "TODO 2-3 句：为什么在这一档 + 当日盘面数字",
         "risk": "TODO 该标的独有的风险"}
    if role in ("情绪小票", "情绪龙"):
        s["gene"] = "TODO 题材基因：历次同类行情中的角色与记忆"
    return s


def link(core: bool) -> dict:
    d = {"name": "TODO", "code": "TODO", "tag": "TODO 环节定位",
         "logic": "TODO 产业地位 | 弹性来源 | 约束条件" if core else "TODO 为什么传导链较远(一句话)",
         "detail": "TODO 200-300 字：地位、弹性来源、约束、当日盘面" if core else "TODO 100-180 字",
         "risk": "TODO"}
    if core:
        d["confirm"] = "TODO 客观确认条件 A / B / C"
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id")
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", default=None)
    ap.add_argument("--mainline", default="TODO 主线（沿用已有主线名，或新建）")
    ap.add_argument("--driver", default="产业周期", help="产业周期|地缘冲突|政策驱动|证伪型|映射型")
    ap.add_argument("--downgrade", action="store_true", help="降档入库: passes 精确数字/可证伪 but fails 预期差 or A股映射")
    args = ap.parse_args(argv)

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.id):
        print("id must be kebab-case ascii, e.g. titanium-dioxide-hike-7")
        return 2
    path = cases_dir() / f"{args.id}.json"
    if path.exists():
        print(f"{path} exists — edit it instead (add a timeline entry for a 主线更新)")
        return 2
    day = args.date or today_cn()
    case = {
        "schemaVersion": 1,
        "id": args.id,
        "date": day,
        "title": args.title,
        "subtitle": "TODO 3-4 个最硬的数字，用 · 分隔",
        "grade": {"tone": "bolt", "text": "⚡ TODO 定性 · TODO 一句话矛盾点"},
        "driver": args.driver,
        "pricing": "TODO 未定价|部分定价|已定价",
        "mainline": args.mainline,
        "archiveLevel": "正式档",
        "relatedCases": [],
        "positionNote": "TODO 一句话定位 55-85 字：事实 + 定价状态结论",
        "pricingDetail": "TODO 定价状态详版 300-800 字：催化时点(首发/扩散/盘中盘后) → 盘面状态(扣 beta 看超额) → 结论",
        "facts": [
            {"key": "核心事实", "value": "TODO 事件本体 + 精确数字 + 出处", "warn": False},
            {"key": "TODO 量级/供需", "value": "TODO", "warn": False},
            {"key": "TODO 结构/格局", "value": "TODO", "warn": False},
            {"key": "TODO 同期对照/扩散", "value": "TODO", "warn": False},
            {"key": "争议点：TODO", "value": "TODO 最强的反方论据", "warn": True},
            {"key": "盘面验证", "value": "TODO 指数、核心标的涨跌与超额、成交、涨停家数、结论", "warn": False},
        ],
        "timeline": [{"when": day, "what": "TODO 催化事件（带时间点）", "why": "TODO 它在主线里的角色"}],
        "verdict": "TODO ① 分水岭时点… ② 传导的关键约束… ③ 待验证的核心变量… 隐藏面：…",
        "rings": [
            {"name": "变化", "verdict": "TODO 实", "points": ["TODO", "TODO"]},
            {"name": "影响", "verdict": "TODO 强", "points": ["TODO", "TODO"]},
            {"name": "业绩", "verdict": "TODO 存疑", "points": ["TODO", "TODO"]},
            {"name": "股价", "verdict": "TODO 未动", "points": ["TODO", "TODO"]},
        ],
        "ringSummary": "TODO 变化X、影响X、业绩X、股价X——一句话结论",
        "assessment": [
            "闭合度 <strong>TODO%</strong>：TODO 逐环说明",
            "边界：TODO 受益 / 中性 / 受损 分别是谁",
            "主线联动：TODO 与已有档案的关系（写档案 id）",
        ],
        "stockTiers": [
            {"title": "🔥 主攻·资源映射", "driver": args.driver, "stocks": [stock("主攻"), stock("主攻")]},
            {"title": "🧬 观察·待验证", "driver": args.driver, "stocks": [stock("观察")]},
            {"title": "⚡ 情绪小票", "driver": args.driver, "stocks": [stock("情绪小票")]},
            {"title": "👑 情绪龙", "driver": args.driver, "stocks": [stock("情绪龙")]},
        ],
        "history": ["TODO 年份 同类行情 + 数字 + 教训", "TODO", "TODO"],
        "coreLinks": [link(True), link(True)],
        "extendedLinks": [link(False)],
        "notInChain": [{"name": "TODO 蹭概念的方向/公司", "code": "—", "logic": "TODO 为什么不在链上"},
                       {"name": "TODO 错误推演", "code": "—", "logic": "TODO"}],
        "decisionChain": [
            {"name": n, "text": POSITION_STEP_TEXT if n == "仓位" else f"TODO {n}", "style": DECISION_STYLE.get(n, "")}
            for n in DECISION_STEPS
        ],
        "scenarios": [
            {"branch": "TODO（基准情形）", "trigger": "TODO", "state": "TODO", "signal": "TODO"},
            {"branch": "TODO", "trigger": "TODO", "state": "TODO", "signal": "TODO"},
            {"branch": "TODO", "trigger": "TODO", "state": "TODO", "signal": "TODO"},
        ],
        "signals": {"verify": ["TODO", "TODO", "TODO", "TODO"], "falsify": ["TODO", "TODO", "TODO", "TODO"]},
        "calendar": [{"when": "TODO", "what": "TODO", "why": "TODO"} for _ in range(4)],
        "sources": "TODO 来源(时间) ｜ 来源(时间) ｜ …",
    }
    if args.downgrade:
        case["archiveLevel"] = "降档"
        case["downgradeBadge"] = DOWNGRADE_BADGE
        case["grade"] = {"tone": "warn", "text": "⚠ 题材催化级 · TODO 为什么降档（预期差已被抹平 / A 股映射缺失）"}
        case["decisionChain"][0]["text"] = "TODO <strong>题材催化级</strong>（降档）：……。基准参照：……"
        case["coreLinks"].insert(0, {
            "name": "（本档无合格主攻标的）", "code": "—", "tag": "TODO 为什么没有合格标的",
            "logic": "产业地位 | — | 弹性来源 | — | 约束条件 | TODO",
            "detail": "TODO 若确无主营相关的 A 股公司，保留这张卡并写明原因；若有，删除这张卡",
            "confirm": "TODO 什么情况下可升级为正式档", "risk": "TODO 强行映射会产生什么误判"})
    write_json(path, case)
    print(f"scaffolded {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
