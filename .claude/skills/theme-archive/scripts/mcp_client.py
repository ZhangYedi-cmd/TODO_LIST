#!/usr/bin/env python3
"""Minimal MCP client (streamable HTTP) for the data servers in the repo's .mcp.json.

    python3 mcp_client.py probe [SERVER ...] [--out tools.json]   # handshake + tools/list per server
    python3 mcp_client.py tools SERVER [--json]                   # one server's tools and their parameters
    python3 mcp_client.py call SERVER TOOL ['{"arg": "value"}']   # call a tool and print its result

Servers come from <repo>/.mcp.json (or --config), the same file Claude Code reads.
${VAR} and ${VAR:-default} in url and headers are expanded from the environment,
so tokens live in environment variables (IFIND_MCP_TOKEN for the iFinD servers)
and never in git.  The transport type may be written "http" (Claude Code) or
"streamablehttp" (the vendor's config).

Exit codes: 0 ok · 1 error · 2 host unreachable (blocked by the network policy
or refused) · 4 authentication failed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ta_common import NetworkBlocked, repo_root, ssl_context  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "theme-archive", "version": "1.0"}
HTTP_TYPES = {"http", "streamablehttp", "streamable-http", "streamable_http"}
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class McpError(RuntimeError):
    """Protocol, HTTP or tool error."""


class AuthFailed(RuntimeError):
    """The server rejected the credentials (HTTP 401/403)."""


def expand(value: str, missing: list[str]) -> str:
    def sub(m: re.Match) -> str:
        name, default = m.group(1), m.group(2)
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            return default
        missing.append(name)
        return ""
    return _VAR.sub(sub, value)


def load_servers(config: str | None = None) -> dict[str, dict]:
    path = Path(config) if config else repo_root() / ".mcp.json"
    if not path.exists():
        raise McpError(f"no MCP config at {path} (pass --config)")
    return json.loads(path.read_text(encoding="utf-8")).get("mcpServers", {})


class Client:
    def __init__(self, name: str, entry: dict, timeout: float = 30):
        kind = str(entry.get("type", "http")).lower()
        if kind not in HTTP_TYPES:
            raise McpError(f"{name}: transport {kind!r} not supported (streamable HTTP only)")
        missing: list[str] = []
        self.name = name
        self.url = expand(entry["url"], missing)
        self.headers = {k: expand(str(v), missing) for k, v in (entry.get("headers") or {}).items()}
        if missing:
            raise McpError(f"{name}: environment variable not set: {', '.join(sorted(set(missing)))}")
        self.timeout = timeout
        self.session: str | None = None
        self.protocol = PROTOCOL_VERSION
        self.server_info: dict = {}
        self._id = 0

    # -------------------------------------------------------------- transport
    def _open(self, payload: dict | None, method: str = "POST"):
        import urllib.error
        import urllib.parse
        import urllib.request

        hdrs = {"Accept": "application/json, text/event-stream", "User-Agent": "theme-archive-mcp/1.0", **self.headers}
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        if self.session:
            hdrs["Mcp-Session-Id"] = self.session
        if not payload or payload.get("method") != "initialize":
            hdrs["MCP-Protocol-Version"] = self.protocol
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(self.url, data=body, headers=hdrs, method=method)
        host = urllib.parse.urlsplit(self.url).netloc
        try:
            return urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context())
        except urllib.error.HTTPError as e:
            if e.code in (403, 407) and "Tunnel" in str(e.reason):
                raise NetworkBlocked(f"{host}: proxy refused the tunnel ({e.code})") from e
            detail = e.read().decode("utf-8", "replace").strip()[:300]
            if e.code in (401, 403):
                raise AuthFailed(f"{self.name}: HTTP {e.code} {detail}") from e
            raise McpError(f"{self.name}: HTTP {e.code} {detail}") from e
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            if "Tunnel connection failed" in str(reason):
                raise NetworkBlocked(f"{host}: {reason}") from e
            if isinstance(reason, (ConnectionError, TimeoutError)) or "timed out" in str(reason).lower():
                raise NetworkBlocked(f"{host}: {type(reason).__name__}: {reason}") from e
            raise McpError(f"{self.name}: {reason}") from e

    def _post(self, payload: dict) -> dict | None:
        import http.client

        resp = self._open(payload)
        try:
            msg = self._reply(resp, payload)
        except (OSError, http.client.HTTPException) as e:
            raise McpError(f"{self.name}: reading the reply to {payload.get('method')}: {e}") from e
        if "id" not in payload:
            return None
        if not isinstance(msg, dict):
            raise McpError(f"{self.name}: no reply to {payload['method']}")
        if "error" in msg:
            err = msg["error"] or {}
            raise McpError(f"{self.name}: {payload['method']} failed ({err.get('code')}): {err.get('message')}")
        return msg.get("result") or {}

    def _reply(self, resp, payload: dict):
        with resp:
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                self.session = sid
            if "id" not in payload:  # notification: 202, no body
                resp.read()
                return None
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "text/event-stream" in ctype:
                msg = _read_sse(resp, payload["id"])
            else:
                raw = resp.read().decode("utf-8", "replace").strip()
                msg = json.loads(raw) if raw else None
                if isinstance(msg, list):
                    msg = next((m for m in msg if isinstance(m, dict) and m.get("id") == payload["id"]), None)
        return msg

    # -------------------------------------------------------------- protocol
    def request(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        payload: dict = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        return self._post(payload) or {}

    def notify(self, method: str) -> None:
        try:
            self._post({"jsonrpc": "2.0", "method": method})
        except McpError:
            pass  # a server that rejects the notification still answers requests

    def initialize(self) -> dict:
        res = self.request("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                          "clientInfo": CLIENT_INFO})
        self.protocol = res.get("protocolVersion") or PROTOCOL_VERSION
        self.server_info = res.get("serverInfo") or {}
        self.notify("notifications/initialized")
        return res

    def list_tools(self) -> list[dict]:
        tools: list[dict] = []
        cursor = None
        while True:
            res = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools += res.get("tools") or []
            cursor = res.get("nextCursor")
            if not cursor:
                return tools

    def call(self, tool: str, arguments: dict) -> dict:
        return self.request("tools/call", {"name": tool, "arguments": arguments})

    def close(self) -> None:
        if self.session:
            try:
                self._open(None, method="DELETE").close()
            except Exception:
                pass


def _read_sse(resp, want_id) -> dict | None:
    """Read SSE events until the JSON-RPC reply with id == want_id arrives."""
    data: list[str] = []

    def flush():
        if not data:
            return None
        text = "\n".join(data)
        data.clear()
        try:
            msg = json.loads(text)
        except ValueError:
            return None
        if isinstance(msg, dict) and msg.get("id") == want_id and ("result" in msg or "error" in msg):
            return msg
        return None

    for raw in resp:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith("data:"):
            value = line[5:]
            data.append(value[1:] if value.startswith(" ") else value)
        elif not line:
            msg = flush()
            if msg:
                return msg
    return flush()


def connect(servers: dict, name: str, timeout: float) -> Client:
    if name not in servers:
        raise McpError(f"unknown server {name!r}; configured: {', '.join(servers)}")
    client = Client(name, servers[name], timeout)
    client.initialize()
    return client


# ------------------------------------------------------------------ commands
def _unprefixed(err: Exception, name: str) -> str:
    text = str(err)
    return text[len(name) + 2:] if text.startswith(name + ": ") else text


def cmd_probe(servers: dict, names: list[str], timeout: float, out: str | None) -> int:
    catalog: dict = {}
    codes: set[int] = set()
    for name in names or list(servers):
        t0 = time.monotonic()
        try:
            client = connect(servers, name, timeout)
            try:
                tools = client.list_tools()
            finally:
                client.close()
        except NetworkBlocked as e:
            print(f"  UNREACHABLE {name}: {e}")
            codes.add(2)
            continue
        except AuthFailed as e:
            print(f"  AUTH FAILED {name}: {_unprefixed(e, name)}")
            codes.add(4)
            continue
        except (McpError, ValueError, KeyError) as e:
            print(f"  FAIL {name}: {_unprefixed(e, name)}")
            codes.add(1)
            continue
        info = client.server_info
        print(f"  ok   {name}: {len(tools)} tools · {info.get('name', '?')} {info.get('version', '')}".rstrip()
              + f" · protocol {client.protocol} · {time.monotonic() - t0:.1f}s")
        names_line = ", ".join(t.get("name", "?") for t in tools)
        print("       " + (names_line[:300] + " …" if len(names_line) > 300 else names_line))
        catalog[name] = {"server": info, "protocol": client.protocol, "tools": tools}
    if out:
        Path(out).write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"tool catalog -> {out}")
    if 2 in codes:
        print("hint: allow the host in the environment's network settings, or run from a machine with normal internet")
    for code in (2, 4, 1):
        if code in codes:
            return code
    return 0


def describe(tool: dict) -> str:
    schema = tool.get("inputSchema") or {}
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    params = ", ".join(f"{k}{'*' if k in required else ''}:{(v or {}).get('type', '?')}" for k, v in props.items())
    first = (tool.get("description") or "").strip().splitlines()
    return f"{tool.get('name')}({params})" + (f"\n      {first[0][:160]}" if first else "")


def render_result(res: dict) -> int:
    if res.get("structuredContent") is not None:
        print(json.dumps(res["structuredContent"], ensure_ascii=False, indent=1))
    else:
        for item in res.get("content") or []:
            if item.get("type") != "text":
                print(f"[{item.get('type')} content omitted]")
                continue
            text = item.get("text", "")
            try:
                print(json.dumps(json.loads(text), ensure_ascii=False, indent=1))
            except ValueError:
                print(text)
    return 1 if res.get("isError") else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="MCP config (default: <repo>/.mcp.json)")
    ap.add_argument("--timeout", type=float, default=30)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe", help="handshake + tools/list on each server")
    p.add_argument("servers", nargs="*")
    p.add_argument("--out", help="write the tool catalog (with input schemas) to this JSON file")
    p = sub.add_parser("tools", help="list one server's tools")
    p.add_argument("server")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("call", help="call one tool")
    p.add_argument("server")
    p.add_argument("tool")
    p.add_argument("arguments", nargs="?", default="{}", help="JSON object, or @file.json")
    p.add_argument("--raw", action="store_true", help="print the raw tools/call result")
    args = ap.parse_args(argv)

    try:
        servers = load_servers(args.config)
        if args.cmd == "probe":
            return cmd_probe(servers, args.servers, args.timeout, args.out)
        client = connect(servers, args.server, args.timeout)
        try:
            if args.cmd == "tools":
                tools = client.list_tools()
                if args.json:
                    print(json.dumps(tools, ensure_ascii=False, indent=1))
                else:
                    for t in tools:
                        print("  " + describe(t))
                return 0
            text = args.arguments
            if text.startswith("@"):
                text = Path(text[1:]).read_text(encoding="utf-8")
            arguments = json.loads(text)
            if not isinstance(arguments, dict):
                raise McpError("tool arguments must be a JSON object")
            res = client.call(args.tool, arguments)
            if args.raw:
                print(json.dumps(res, ensure_ascii=False, indent=1))
                return 1 if res.get("isError") else 0
            return render_result(res)
        finally:
            client.close()
    except NetworkBlocked as e:
        print(f"unreachable: {e}\nhint: allow the host in the environment's network settings")
        return 2
    except AuthFailed as e:
        print(f"authentication failed: {e}")
        return 4
    except (McpError, ValueError) as e:
        print(f"error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
