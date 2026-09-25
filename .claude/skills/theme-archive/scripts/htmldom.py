"""Minimal DOM over the stdlib HTMLParser that remembers exact source offsets.

Only used by import_html.py: it lets us pull the *raw* inner HTML of an element
out of an existing archive file, byte for byte, so a round-trip
(import -> build) reproduces the original page exactly.
"""
from __future__ import annotations

from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "parent", "children", "start", "inner_start", "inner_end", "end")

    def __init__(self, tag, attrs, parent, start, inner_start):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children: list[Node] = []
        self.start = start
        self.inner_start = inner_start
        self.inner_end = inner_start
        self.end = inner_start

    # ---- queries -------------------------------------------------------
    @property
    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    def has_class(self, cls: str) -> bool:
        return cls in self.classes

    def iter(self):
        for c in self.children:
            yield c
            yield from c.iter()

    def find_all(self, tag: str | None = None, cls: str | None = None, recursive: bool = True):
        pool = self.iter() if recursive else iter(self.children)
        return [n for n in pool if (tag is None or n.tag == tag) and (cls is None or n.has_class(cls))]

    def find(self, tag: str | None = None, cls: str | None = None, recursive: bool = True):
        r = self.find_all(tag, cls, recursive)
        return r[0] if r else None

    def kids(self, tag: str | None = None, cls: str | None = None):
        return self.find_all(tag, cls, recursive=False)


class _Builder(HTMLParser):
    def __init__(self, src: str):
        super().__init__(convert_charrefs=False)
        self.src = src
        self._line_off = [0]
        for i, ch in enumerate(src):
            if ch == "\n":
                self._line_off.append(i + 1)
        self.root = Node("#root", {}, None, 0, 0)
        self.root.inner_end = self.root.end = len(src)
        self.stack = [self.root]

    def _off(self) -> int:
        line, col = self.getpos()
        return self._line_off[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self._off()
        raw = self.get_starttag_text() or ""
        node = Node(tag, attrs, self.stack[-1], start, start + len(raw))
        self.stack[-1].children.append(node)
        if tag in VOID:
            node.end = node.inner_end = node.inner_start
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        start = self._off()
        raw = self.get_starttag_text() or ""
        node = Node(tag, attrs, self.stack[-1], start, start + len(raw))
        node.end = node.inner_end = node.inner_start
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        pos = self._off()
        # pop to the matching open element (tolerates sloppy markup)
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                end_len = self.src.index(">", pos) + 1 - pos
                for n in self.stack[i + 1:]:  # unclosed descendants end here
                    n.inner_end = n.end = pos
                self.stack[i].inner_end = pos
                self.stack[i].end = pos + end_len
                del self.stack[i:]
                return


def parse(src: str) -> Node:
    b = _Builder(src)
    b.feed(src)
    b.close()
    return b.root


class Doc:
    """Convenience wrapper: node -> raw inner/outer HTML and plain text."""

    def __init__(self, src: str):
        self.src = src
        self.root = parse(src)

    def inner(self, node: Node | None) -> str:
        return "" if node is None else self.src[node.inner_start:node.inner_end]

    def outer(self, node: Node | None) -> str:
        return "" if node is None else self.src[node.start:node.end]

    def text(self, node: Node | None) -> str:
        import html
        import re

        if node is None:
            return ""
        return html.unescape(re.sub(r"<[^>]+>", "", self.inner(node)))
