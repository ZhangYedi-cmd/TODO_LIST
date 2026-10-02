"""Shared constants, paths and small helpers for the theme-archive skill.

Everything here is stdlib-only so the skill runs on a bare Python 3.9+.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_DIR / "assets"

# ---------------------------------------------------------------- enums
PRICING = ["未定价", "部分定价", "已定价"]
DRIVERS = ["产业周期", "地缘冲突", "政策驱动", "证伪型", "映射型"]
ARCHIVE_LEVELS = ["正式档", "降档"]
# grade tone -> emoji used as the first character of grade.text
TONES = {"fire": "🔥", "bolt": "⚡", "warn": "⚠"}
RING_NAMES = ["变化", "影响", "业绩", "股价"]
DECISION_STEPS = ["定性", "主攻优先级", "情绪优先级", "确认条件", "验证点", "证伪点", "仓位", "特别提醒"]
DECISION_STYLE = {"仓位": "dim", "特别提醒": "alert"}
POSITION_STEP_TEXT = "交易者自管，本图不涉及。"
# stock-tier roles, in the order they are rendered
ROLES = [
    ("主攻", "🔥"),
    ("容量中军", "🏛️"),
    ("观察", "🧬"),
    ("情绪小票", "⚡"),
    ("情绪龙", "👑"),
]
ROLE_DEFAULT_TITLE = {
    "主攻": "🔥 主攻·资源映射",
    "容量中军": "🏛️ 容量中军",
    "观察": "🧬 观察·待验证",
    "情绪小票": "⚡ 情绪小票",
    "情绪龙": "👑 情绪龙",
}
DOWNGRADE_BADGE = "⚑ 降档入库 · 只配情绪波段，不格局中线"

# fixed prefixes the renderer adds in front of stored text
PREFIX = {
    "gene": "🧬 题材基因：",
    "confirm": "✔ 确认：",
    "risk": "⚠️ ",
    "why": "为什么：",
    "summary": "▸ ",
    "branch": "▸ ",
}


def role_of_title(title: str) -> str | None:
    for role, _emoji in ROLES:
        if role in title:
            return role
    return None


# ---------------------------------------------------------------- paths
def repo_root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except Exception:
        return SKILL_DIR.parents[2]


def archive_home() -> Path:
    env = os.environ.get("THEME_ARCHIVE_HOME")
    home = Path(env).expanduser() if env else repo_root() / "theme-archive"
    return home


def cases_dir() -> Path:
    return archive_home() / "cases"


def data_dir(day: str | None = None) -> Path:
    base = archive_home() / "data"
    return base / day.replace("-", "") if day else base


def dist_dir() -> Path:
    return archive_home() / "dist"


# ---------------------------------------------------------------- io
def read_json(path: Path | str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path | str, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def load_cases(directory: Path | None = None) -> list[dict]:
    directory = directory or cases_dir()
    cases = []
    for p in sorted(Path(directory).glob("*.json")):
        c = read_json(p)
        c.setdefault("id", p.stem)
        cases.append(c)
    return cases


# ---------------------------------------------------------------- text
_TAG = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    import html

    return html.unescape(_TAG.sub("", s or ""))


def md_bold(s: str) -> str:
    """Turn **bold** into <strong>bold</strong> (the original renderer leaked raw **)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s or "")


# ---------------------------------------------------------------- dates
CN_TZ = _dt.timezone(_dt.timedelta(hours=8))


def now_cn() -> _dt.datetime:
    return _dt.datetime.now(CN_TZ)


def today_cn() -> str:
    return now_cn().strftime("%Y-%m-%d")


def md(day: str) -> str:
    """2026-09-16 -> 9/16"""
    d = _dt.date.fromisoformat(day)
    return f"{d.month}/{d.day}"


# ---------------------------------------------------------------- trading calendar
# Weekday exchange holidays (SSE/SZSE/BSE notices).  Weekend make-up workdays are
# still closed for trading, so only weekdays need listing.  Add next year's list
# when the exchanges publish it (usually late December).
EXCHANGE_HOLIDAYS = {
    2026: {
        "2026-01-01", "2026-01-02",                                   # 元旦
        "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-23",  # 春节
        "2026-04-06",                                                 # 清明
        "2026-05-01", "2026-05-04", "2026-05-05",                     # 劳动节
        "2026-06-19",                                                 # 端午
        "2026-09-25",                                                 # 中秋
        "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07",  # 国庆
    },
}


def is_trading_day(day: str) -> bool:
    d = _dt.date.fromisoformat(day)
    if d.weekday() >= 5:
        return False
    return day not in EXCHANGE_HOLIDAYS.get(d.year, set())


def calendar_known(day: str) -> bool:
    return _dt.date.fromisoformat(day).year in EXCHANGE_HOLIDAYS


def last_trading_day(day: str, include_self: bool = True) -> str:
    d = _dt.date.fromisoformat(day)
    if not include_self:
        d -= _dt.timedelta(days=1)
    while not is_trading_day(d.isoformat()):
        d -= _dt.timedelta(days=1)
    return d.isoformat()


def prev_trading_day(day: str) -> str:
    return last_trading_day(day, include_self=False)


def session_of(ts: str, day: str | None = None) -> str:
    """Classify a CN timestamp 'YYYY-MM-DD HH:MM[:SS]' relative to the A-share session.

    Returns one of 盘前 / 盘中 / 午间 / 盘后 / 夜间 / 非交易日.
    """
    ts = ts.strip().replace("T", " ")
    date_part, _, time_part = ts.partition(" ")
    if not is_trading_day(date_part):
        return "非交易日"
    hhmm = time_part[:5] or "00:00"
    if hhmm < "09:30":
        return "盘前"
    if hhmm < "11:30":
        return "盘中"
    if hhmm < "13:00":
        return "午间"
    if hhmm < "15:00":
        return "盘中"
    if hhmm < "20:00":
        return "盘后"
    return "夜间"


# ---------------------------------------------------------------- http
class NetworkBlocked(RuntimeError):
    """Raised when an egress proxy / firewall refuses the host."""


def ssl_context():
    """Default TLS context that also trusts SSL_CERT_FILE / REQUESTS_CA_BUNDLE (e.g. an egress proxy CA)."""
    import ssl
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=cafile) if cafile and os.path.exists(cafile) else ssl.create_default_context()


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def http_get(url: str, *, params: dict | None = None, headers: dict | None = None, data: dict | None = None,
             timeout: float = 15, retries: int = 2, encoding: str | None = None) -> str:
    """GET (or form POST when data is given) with retries; honours HTTPS_PROXY and SSL_CERT_FILE."""
    import gzip
    import time
    import urllib.error
    import urllib.parse
    import urllib.request
    import zlib

    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    hdrs = {"User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip, deflate", "Accept-Language": "zh-CN,zh;q=0.9"}
    hdrs.update(headers or {})
    ctx = ssl_context()
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
                enc = (resp.headers.get("Content-Encoding") or "").lower()
                if enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    raw = zlib.decompress(raw)
                charset = encoding or resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 407) and "Tunnel" in str(e.reason):
                raise NetworkBlocked(f"{urllib.parse.urlsplit(url).hostname}: {e}") from e
            if e.code < 500:
                raise
        except (urllib.error.URLError, OSError) as e:
            last = e
            msg = str(getattr(e, "reason", e))
            if "Tunnel connection failed: 403" in msg or "Tunnel connection failed: 407" in msg:
                raise NetworkBlocked(f"{urllib.parse.urlsplit(url).hostname}: {msg}") from e
        time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


def http_json(url: str, **kw):
    text = http_get(url, **kw).strip()
    m = re.match(r"^[\w$.]+\((.*)\)\s*;?\s*$", text, re.S)  # strip JSONP
    if m:
        text = m.group(1)
    return json.loads(text)
