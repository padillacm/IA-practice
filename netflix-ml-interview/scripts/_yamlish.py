"""Tiny YAML-subset loader/dumper (stdlib only), shared by sim.py and check_simulator.py.

Supported subset:
  * block maps and block lists (2-space indentation recommended, tabs forbidden)
  * list items that start a map ("- id: x" followed by more keys)
  * flow lists "[a, b]" and flow maps "{a: 1, b: x}" on a single line
  * scalars: null/~, true/false, ints, floats, "double" and 'single' quoted strings,
    plain strings (never converted to dates; yes/no/on/off stay strings)
  * literal "|" and folded ">" block scalars (with -/+ chomping)
  * "#" comments (full line, or after whitespace outside quotes)
Not supported: anchors/aliases, tags, multi-document files, multi-line plain
scalars, multi-line flow collections, complex keys. Map keys are always strings.
"""
from __future__ import annotations

import json
import re

__all__ = ["YamlError", "loads", "dumps", "split_front_matter", "join_front_matter",
           "parse_scalar", "parse_inline", "extract_yaml_block"]


class YamlError(ValueError):
    """Raised when text falls outside the supported YAML subset."""


_INT = re.compile(r"^[+-]?(0|[1-9][0-9]*)$")
_FLOAT = re.compile(r"^[+-]?([0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)([eE][+-]?[0-9]+)?$")
_PLAIN_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.@/\-]*\Z")


# ---------------------------------------------------------------- scalars
def parse_scalar(text: str):
    """Convert one plain or quoted scalar token to a Python value."""
    s = text.strip()
    if s == "":
        return None
    if s[0] == '"':
        return _unquote_double(s)
    if s[0] == "'":
        if len(s) < 2 or s[-1] != "'":
            raise YamlError(f"unterminated single-quoted string: {s}")
        return s[1:-1].replace("''", "'")
    if s in ("null", "Null", "NULL", "~"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if _INT.match(s):
        return int(s)
    if _FLOAT.match(s) and any(c in s for c in ".eE"):
        return float(s)
    return s


def _unquote_double(s: str) -> str:
    if len(s) < 2 or s[-1] != '"':
        raise YamlError(f"unterminated double-quoted string: {s}")
    try:
        return json.loads(s)
    except ValueError as exc:
        raise YamlError(f"bad escape in double-quoted string: {s}") from exc


def _scan_quoted(s: str, start: int) -> int:
    """Return the index just past the quoted token starting at ``start``."""
    q = s[start]
    i = start + 1
    while i < len(s):
        c = s[i]
        if q == '"' and c == "\\":
            i += 2
            continue
        if c == q:
            if q == "'" and i + 1 < len(s) and s[i + 1] == "'":
                i += 2
                continue
            return i + 1
        i += 1
    raise YamlError(f"unterminated quoted string: {s}")


def _strip_comment(s: str) -> str:
    """Remove a trailing ' #...' comment that is outside quotes."""
    i = 0
    while i < len(s):
        c = s[i]
        prev = s[i - 1] if i else None
        if c in "\"'" and prev in (None, " ", "[", "{", ","):
            try:
                i = _scan_quoted(s, i)
            except YamlError:
                return s
            continue
        if c == "#" and prev in (None, " "):
            return s[:i]
        i += 1
    return s


# ------------------------------------------------------------------- flow
def parse_inline(s: str):
    """Parse a single-line value: flow list/map, quoted string or plain scalar."""
    s = s.strip()
    if s[:1] in ("[", "{"):
        value, end = _flow(s, 0)
        if s[end:].strip():
            raise YamlError(f"trailing text after flow collection: {s}")
        return value
    return parse_scalar(s)


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] == " ":
        i += 1
    return i


def _flow(s: str, i: int):
    i = _skip_ws(s, i)
    if i >= len(s):
        raise YamlError("unexpected end of flow collection")
    if s[i] == "[":
        return _flow_list(s, i + 1)
    if s[i] == "{":
        return _flow_map(s, i + 1)
    return _flow_scalar(s, i, ",]}")


def _flow_scalar(s: str, i: int, stops: str):
    if s[i] in "\"'":
        end = _scan_quoted(s, i)
        return parse_scalar(s[i:end]), end
    j = i
    while j < len(s) and s[j] not in stops:
        j += 1
    return parse_scalar(s[i:j]), j


def _flow_list(s: str, i: int):
    items = []
    i = _skip_ws(s, i)
    if i < len(s) and s[i] == "]":
        return items, i + 1
    while True:
        value, i = _flow(s, i)
        items.append(value)
        i = _skip_ws(s, i)
        if i >= len(s):
            raise YamlError("unterminated flow list")
        if s[i] == ",":
            i += 1
            continue
        if s[i] == "]":
            return items, i + 1
        raise YamlError(f"unexpected character in flow list: {s[i]!r}")


def _flow_map(s: str, i: int):
    result = {}
    i = _skip_ws(s, i)
    if i < len(s) and s[i] == "}":
        return result, i + 1
    while True:
        i = _skip_ws(s, i)
        key, i = _flow_scalar(s, i, ":,}")
        i = _skip_ws(s, i)
        if i >= len(s) or s[i] != ":":
            raise YamlError("expected ':' in flow map")
        value, i = _flow(s, i + 1)
        result[str(key)] = value
        i = _skip_ws(s, i)
        if i >= len(s):
            raise YamlError("unterminated flow map")
        if s[i] == ",":
            i += 1
            continue
        if s[i] == "}":
            return result, i + 1
        raise YamlError(f"unexpected character in flow map: {s[i]!r}")


# ----------------------------------------------------------------- parser
class _Line:
    __slots__ = ("indent", "text", "no")

    def __init__(self, indent: int, text: str, no: int):
        self.indent, self.text, self.no = indent, text, no


def _is_item(text: str) -> bool:
    return text == "-" or text.startswith("- ")


def _split_key(text: str):
    """Return (key, rest) when ``text`` is a map entry, else None."""
    if text[:1] in ("[", "{"):
        return None
    if text[:1] in "\"'":
        try:
            end = _scan_quoted(text, 0)
        except YamlError:
            return None
        if text[end:end + 1] != ":" or (len(text) > end + 1 and text[end + 1] != " "):
            return None
        return parse_scalar(text[:end]), text[end + 1:].strip()
    m = re.search(r":(?: |$)", text)
    if not m:
        return None
    return text[:m.start()].strip(), text[m.end():].strip()


class _Parser:
    def __init__(self, text: str):
        self.raw = text.replace("\r\n", "\n").split("\n")
        self.lines: list[_Line] = []
        for no, raw in enumerate(self.raw):
            body = raw.lstrip(" ")
            if body.startswith("\t") or "\t" in raw[:len(raw) - len(body)]:
                raise YamlError(f"line {no + 1}: tab used for indentation")
            clean = _strip_comment(body).rstrip()
            if clean and clean != "---":
                self.lines.append(_Line(len(raw) - len(body), clean, no))
        self.i = 0

    def parse(self):
        if not self.lines:
            return None
        value = self._block(self.lines[0].indent)
        if self.i < len(self.lines):
            ln = self.lines[self.i]
            raise YamlError(f"line {ln.no + 1}: unexpected content")
        return value

    def _block(self, indent: int):
        ln = self.lines[self.i]
        if _is_item(ln.text):
            return self._list(indent)
        if _split_key(ln.text) is not None:
            return self._map(indent)
        self.i += 1
        return parse_inline(ln.text)

    def _map(self, indent: int) -> dict:
        result: dict = {}
        while self.i < len(self.lines):
            ln = self.lines[self.i]
            if ln.indent < indent:
                break
            if ln.indent > indent:
                raise YamlError(f"line {ln.no + 1}: unexpected indentation")
            kv = _split_key(ln.text)
            if kv is None:
                raise YamlError(f"line {ln.no + 1}: expected 'key: value'")
            key, rest = kv
            if key in result:
                raise YamlError(f"line {ln.no + 1}: duplicate key {key!r}")
            self.i += 1
            result[str(key)] = self._value(rest, ln)
        return result

    def _value(self, rest: str, ln: _Line):
        if rest == "":
            nxt = self.lines[self.i] if self.i < len(self.lines) else None
            if nxt is None:
                return None
            if nxt.indent > ln.indent:
                return self._block(nxt.indent)
            if nxt.indent == ln.indent and _is_item(nxt.text):
                return self._list(ln.indent)
            return None
        if rest[0] in "|>" and re.match(r"^[|>][+-]?$", rest):
            return self._block_scalar(rest, ln)
        return parse_inline(rest)

    def _list(self, indent: int) -> list:
        items: list = []
        while self.i < len(self.lines):
            ln = self.lines[self.i]
            if ln.indent < indent:
                break
            if ln.indent > indent:
                raise YamlError(f"line {ln.no + 1}: unexpected indentation")
            if not _is_item(ln.text):
                break
            rest = ln.text[1:].lstrip(" ")
            offset = len(ln.text) - len(rest)
            if rest == "":
                self.i += 1
                nxt = self.lines[self.i] if self.i < len(self.lines) else None
                items.append(self._block(nxt.indent) if nxt and nxt.indent > indent else None)
            elif _is_item(rest):
                self.lines[self.i] = _Line(indent + offset, rest, ln.no)
                items.append(self._list(indent + offset))
            elif _split_key(rest) is not None:
                self.lines[self.i] = _Line(indent + offset, rest, ln.no)
                items.append(self._map(indent + offset))
            else:
                self.i += 1
                items.append(parse_inline(rest))
        return items

    def _block_scalar(self, header: str, ln: _Line) -> str:
        fold, chomp = header[0] == ">", header[1:]
        body: list[str] = []
        block_indent = None
        no = ln.no + 1
        while no < len(self.raw):
            raw = self.raw[no]
            if raw.strip() == "":
                body.append("")
                no += 1
                continue
            ind = len(raw) - len(raw.lstrip(" "))
            if ind <= ln.indent:
                break
            block_indent = ind if block_indent is None else block_indent
            if ind < block_indent:
                break
            body.append(raw[block_indent:])
            no += 1
        while self.i < len(self.lines) and self.lines[self.i].no < no:
            self.i += 1
        trailing = 0
        while body and body[-1] == "":
            body.pop()
            trailing += 1
        text = _fold(body) if fold else "\n".join(body)
        if chomp == "-" or not body:
            return text
        return text + ("\n" * trailing if chomp == "+" and trailing else "\n")


def _fold(lines: list[str]) -> str:
    out, buf = [], []
    for line in lines:
        if line == "":
            out.append(" ".join(buf))
            buf = []
        else:
            buf.append(line)
    out.append(" ".join(buf))
    return "\n".join(out)


def loads(text: str):
    """Parse YAML-subset text into Python objects."""
    return _Parser(text).parse()


# ------------------------------------------------------------------ dumper
def _needs_quotes(s: str, flow: bool) -> bool:
    if s == "" or s != s.strip() or "\n" in s or "\r" in s or "\t" in s:
        return True
    if s[0] in "-?:,[]{}#&*!|>'\"%@`" and not (s[0] == "-" and len(s) > 1 and s[1] not in " -"):
        return True
    if ": " in s or " #" in s or s.endswith(":") or s == "---":
        return True
    if flow and any(c in s for c in ",[]{}"):
        return True
    if not isinstance(parse_scalar(s), str):
        return True
    return any(ord(c) < 32 for c in s)


def _fmt_scalar(v, flow: bool = False) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v)
    return json.dumps(s, ensure_ascii=False) if _needs_quotes(s, flow) else s


def _fmt_key(k) -> str:
    s = str(k)
    return s if _PLAIN_KEY.match(s) and isinstance(parse_scalar(s), str) else json.dumps(s, ensure_ascii=False)


def _is_scalar(v) -> bool:
    return not isinstance(v, (dict, list, tuple))


def _flow_inline(v) -> str | None:
    """Single-line form for scalars, empty collections and short scalar lists."""
    if _is_scalar(v):
        return _fmt_scalar(v)
    if isinstance(v, dict) and not v:
        return "{}"
    if isinstance(v, (list, tuple)):
        if not v:
            return "[]"
        if all(_is_scalar(x) for x in v):
            line = "[" + ", ".join(_fmt_scalar(x, True) for x in v) + "]"
            return line if len(line) <= 88 else None
    return None


def _emit(obj, ind: int, out: list[str]) -> None:
    pad = " " * ind
    if isinstance(obj, dict):
        for k, v in obj.items():
            inline = _flow_inline(v)
            if inline is not None:
                out.append(f"{pad}{_fmt_key(k)}: {inline}")
            else:
                out.append(f"{pad}{_fmt_key(k)}:")
                _emit(v, ind + 2, out)
    else:
        for item in obj:
            inline = _flow_inline(item)
            if inline is not None:
                out.append(f"{pad}- {inline}")
                continue
            sub: list[str] = []
            _emit(item, ind + 2, sub)
            sub[0] = pad + "- " + sub[0][ind + 2:]
            out.extend(sub)


def dumps(obj) -> str:
    """Serialize Python objects to YAML-subset text (loads(dumps(x)) == x)."""
    inline = _flow_inline(obj)
    if inline is not None:
        return inline + "\n"
    out: list[str] = []
    _emit(obj, 0, out)
    return "\n".join(out) + "\n"


# ----------------------------------------------------------- front matter
def split_front_matter(text: str):
    """Split '---\\n<yaml>\\n---\\n<body>' into (dict, body). No front matter -> ({}, text)."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    while end != -1 and text[end + 4:end + 5] not in ("", "\n"):
        end = text.find("\n---", end + 1)
    if end == -1:
        return {}, text
    meta = loads(text[4:end]) or {}
    if not isinstance(meta, dict):
        raise YamlError("front matter must be a map")
    return meta, text[end + 5:].lstrip("\n") if text[end + 4:end + 5] == "\n" else ""


def join_front_matter(meta: dict, body: str) -> str:
    """Inverse of split_front_matter."""
    return "---\n" + dumps(meta) + "---\n\n" + body.lstrip("\n")


_FENCE = re.compile(r"```ya?ml[ \t]*\n(.*?)\n```", re.S)


def extract_yaml_block(text: str):
    """Parse the first fenced ```yaml block in ``text``; None when absent."""
    m = _FENCE.search(text.replace("\r\n", "\n"))
    return loads(m.group(1)) if m else None
