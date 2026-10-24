"""Minimal, safe unified-diff applier (stdlib only).

Applies a diff to files under a root directory. All files are computed in memory
first, so a failing hunk leaves the workspace untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(ValueError):
    """The diff is malformed, unsafe, or does not match the files."""


def parse_patch(text: str) -> list[dict]:
    """Parse a unified diff into [{old, new, hunks:[{start, ops:[(op, line)], no_eol}]}]."""
    lines = text.replace("\r\n", "\n").split("\n")
    files, i = [], 0
    while i < len(lines):
        if lines[i].startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            fp = {"old": _clean(lines[i][4:]), "new": _clean(lines[i + 1][4:]), "hunks": []}
            i += 2
            while i < len(lines) and _HUNK.match(lines[i]):
                hunk, i = _read_hunk(lines, i)
                fp["hunks"].append(hunk)
            if not fp["hunks"]:
                raise PatchError(f"no hunks for {fp['new']}")
            files.append(fp)
        else:
            i += 1
    if not files:
        raise PatchError("no file sections found in the diff")
    return files


def _clean(path: str) -> str:
    return path.split("\t")[0].strip()


def _read_hunk(lines, i):
    m = _HUNK.match(lines[i])
    old_n = int(m.group(2)) if m.group(2) is not None else 1
    new_n = int(m.group(4)) if m.group(4) is not None else 1
    ops, no_eol, i = [], False, i + 1
    while i < len(lines) and (old_n > 0 or new_n > 0 or lines[i].startswith("\\")):
        line = lines[i]
        if line.startswith("\\"):
            no_eol = no_eol or bool(ops and ops[-1][0] in "+ ")
        elif line.startswith("+"):
            ops.append(("+", line[1:]))
            new_n -= 1
        elif line.startswith("-"):
            ops.append(("-", line[1:]))
            old_n -= 1
        else:
            ops.append((" ", line[1:] if line.startswith(" ") else line))
            old_n -= 1
            new_n -= 1
        i += 1
    return {"start": int(m.group(1)), "ops": ops, "no_eol": no_eol}, i


def _safe_target(root: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or rel.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", rel) or ".." in p.parts:
        raise PatchError(f"unsafe path in diff: {rel}")
    target = (root / p).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise PatchError(f"path escapes the workspace: {rel}") from exc
    return target


def _candidates(path: str) -> list[str]:
    """Path spellings to try: as written, without a/ b/ prefix, without 'workspace/'."""
    out = [path]
    if path.startswith(("a/", "b/")):
        out.append(path[2:])
    for p in list(out):
        if p.startswith("workspace/"):
            out.append(p[len("workspace/"):])
    return out


def _resolve(root: Path, fp: dict) -> tuple[str, str]:
    """Return (kind, relpath) with kind in create|delete|modify."""
    if fp["old"] == "/dev/null":
        return "create", _candidates(fp["new"])[1 if fp["new"].startswith("b/") else 0]
    path = fp["old"] if fp["new"] == "/dev/null" else fp["new"]
    cands = _candidates(path)
    for cand in cands:
        if _safe_target(root, cand).is_file():
            return ("delete" if fp["new"] == "/dev/null" else "modify"), cand
    raise PatchError(f"file not found in workspace: {path}")


def _apply_hunks(content: str, hunks: list[dict], path: str) -> str:
    crlf = "\r\n" in content
    text = content.replace("\r\n", "\n")
    ends_nl = text.endswith("\n")
    lines = text.split("\n")[:-1] if ends_nl else (text.split("\n") if text else [])
    shift = 0
    for h in hunks:
        old = [l for op, l in h["ops"] if op in " -"]
        new = [l for op, l in h["ops"] if op in " +"]
        pos = _locate(lines, old, h["start"] - 1 + shift)
        if pos is None:
            raise PatchError(f"hunk at line {h['start']} does not match {path}")
        lines[pos:pos + len(old)] = new
        shift += len(new) - len(old)
        if h["no_eol"] and pos + len(new) >= len(lines):
            ends_nl = False
    out = "\n".join(lines) + ("\n" if ends_nl and lines else "")
    return out.replace("\n", "\r\n") if crlf else out


def _locate(lines: list[str], old: list[str], preferred: int):
    """Index where ``old`` matches, searching outwards from ``preferred``."""
    if not old:
        return max(0, min(preferred, len(lines)))
    limit = len(lines) - len(old)
    for dist in range(0, len(lines) + abs(preferred) + 2):
        for pos in {preferred - dist, preferred + dist}:
            if 0 <= pos <= limit and all(a.rstrip() == b.rstrip() for a, b in zip(lines[pos:pos + len(old)], old)):
                return pos
    return None


def _read_exact(path: Path) -> str:
    """Read text without newline translation (Path.read_text gained newline= only in 3.13)."""
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def apply_patch(root, text: str, dry_run: bool = False) -> list[dict]:
    """Apply ``text`` under ``root``; returns [{path, action, added, removed}]."""
    root = Path(root)
    plan = []
    for fp in parse_patch(text):
        kind, rel = _resolve(root, fp)
        target = _safe_target(root, rel)
        added = sum(1 for h in fp["hunks"] for op, _ in h["ops"] if op == "+")
        removed = sum(1 for h in fp["hunks"] for op, _ in h["ops"] if op == "-")
        if kind == "create":
            if target.exists():
                raise PatchError(f"file already exists: {rel}")
            content = "\n".join(l for h in fp["hunks"] for op, l in h["ops"] if op == "+") + "\n"
        elif kind == "delete":
            content = None
        else:
            content = _apply_hunks(_read_exact(target), fp["hunks"], rel)
        plan.append({"path": rel, "target": target, "action": kind, "content": content,
                     "added": added, "removed": removed})
    if not dry_run:
        for item in plan:
            if item["action"] == "delete":
                item["target"].unlink()
            else:
                item["target"].parent.mkdir(parents=True, exist_ok=True)
                item["target"].write_text(item["content"], encoding="utf-8", newline="")
    return [{k: v for k, v in item.items() if k not in ("target", "content")} for item in plan]
