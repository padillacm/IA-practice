"""Parsers for the markdown content formats frozen in design.md D10 (stdlib only).

Shared by sim.py (question selection, transcripts) and check_simulator.py (validation).
"""
from __future__ import annotations

import re

import _yamlish as yamlish

LEVELS = ("L4", "L5", "L6")
ROLES = ("mle", "rs", "ds")
SCORES = ("SN", "N", "Y", "SY", "no_evidence")
SCORE_RANK = {"SN": 0, "N": 1, "Y": 2, "SY": 3}
MEMO_VALUES = ("selflessness", "judgment", "candor", "creativity", "courage",
               "inclusion", "curiosity", "resilience")
QUESTION_KINDS = ("main", "followup", "culture")

_Q_HEADING = re.compile(r"^###\s+(\S+)\s*$", re.M)
_COMP_HEADING = re.compile(r"^##\s+(\S+)\s*$", re.M)
_TURN_HEADING = re.compile(r"^### T(\d+) · (interviewer|candidate|orchestrator|ai-pair) · t=(\d+)m[ \t]*$", re.M)


# --------------------------------------------------------------- questions
def parse_questions(text: str) -> list[dict]:
    """Return [{id, meta, body, error}] for each '### <id>' section of questions.md.

    ``meta`` is the first fenced yaml block ({} when missing/invalid, with ``error`` set);
    ``body`` is the text after that block (statement and follow-ups).
    """
    text = text.replace("\r\n", "\n")
    heads = list(_Q_HEADING.finditer(text))
    out = []
    for n, m in enumerate(heads):
        end = heads[n + 1].start() if n + 1 < len(heads) else len(text)
        section = text[m.end():end]
        item = {"id": m.group(1), "meta": {}, "body": section.strip(), "error": None}
        fence = re.search(r"```ya?ml[ \t]*\n(.*?)\n```", section, re.S)
        if not fence:
            item["error"] = "missing fenced yaml block"
        else:
            try:
                meta = yamlish.loads(fence.group(1))
                if isinstance(meta, dict):
                    item["meta"] = meta
                else:
                    item["error"] = "yaml block is not a map"
            except yamlish.YamlError as exc:
                item["error"] = f"invalid yaml block: {exc}"
            item["body"] = (section[:fence.start()] + section[fence.end():]).strip()
        out.append(item)
    return out


def variant_of(meta: dict) -> str:
    """Normalized variant of a question/problem; missing/'-'/'any' count as 'default'."""
    v = meta.get("variant")
    return "default" if v in (None, "", "-", "none", "any", "*") else str(v)


def matches(meta: dict, role: str, level: str, variant: str, domain: str) -> bool:
    """True when an item (question/material front matter) fits the session."""
    roles = meta.get("roles") or list(ROLES)
    levels = meta.get("levels") or list(LEVELS)
    item_domain = meta.get("domain") or "any"
    mv = variant_of(meta)
    return (role in roles and level in levels and item_domain in ("any", domain)
            and (mv == variant or meta.get("variant") in (None, "any", "*")))


# ------------------------------------------------------------------ rubric
def parse_rubric(text: str) -> dict:
    """Parse rubric.md into {front, shared, competencies:[{id, core, memo_values, levels, raw}]}.

    A '## <id>' section is a competency when it has a 'core:' line.
    """
    front, body = yamlish.split_front_matter(text)
    body = body.replace("\r\n", "\n")
    heads = list(_COMP_HEADING.finditer(body))
    shared_parts = [body[:heads[0].start()]] if heads else [body]
    comps = []
    for n, m in enumerate(heads):
        end = heads[n + 1].start() if n + 1 < len(heads) else len(body)
        section = body[m.end():end]
        core = re.search(r"^\s*core:\s*(true|false)\s*$", section, re.M | re.I)
        if not core:
            shared_parts.append(body[m.start():end])
            continue
        mv = re.search(r"^\s*memo_values:\s*(.+)$", section, re.M)
        values = None
        if mv:
            try:
                parsed = yamlish.parse_inline(mv.group(1))
                values = [str(x) for x in parsed] if isinstance(parsed, list) else None
            except yamlish.YamlError:
                values = None
        comps.append({"id": m.group(1), "core": core.group(1).lower() == "true",
                      "memo_values": values, "levels": parse_level_table(section), "raw": section})
    return {"front": front, "shared": "\n".join(shared_parts), "competencies": comps}


def parse_level_table(section: str) -> dict:
    """Extract {'L4': bar, ...} from a '| Level | Yes bar |' markdown table."""
    bars = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and line.strip().startswith("|") and cells[0] in LEVELS:
            bars[cells[0]] = " ".join(cells[1:]).strip()
    return bars


# -------------------------------------------------------------- transcript
def parse_transcript(text: str):
    """Return (front_matter, turns); each turn is {n, role, t, body}."""
    front, body = yamlish.split_front_matter(text)
    body = body.replace("\r\n", "\n")
    heads = list(_TURN_HEADING.finditer(body))
    turns = []
    for k, m in enumerate(heads):
        end = heads[k + 1].start() if k + 1 < len(heads) else len(body)
        turns.append({"n": int(m.group(1)), "role": m.group(2), "t": int(m.group(3)),
                      "body": body[m.end():end].strip("\n")})
    return front, turns


def strip_notes_private(body: str) -> str:
    """Remove the top-level ``notes_private`` entry from every <meta> block of ``body``."""
    def clean(match: re.Match) -> str:
        kept, skipping = [], False
        for line in match.group(2).split("\n"):
            if re.match(r"^notes_private\s*:", line):
                skipping = True
                continue
            if skipping and (line.strip() == "" or line[:1] in (" ", "\t", "-")):
                continue
            skipping = False
            kept.append(line)
        return match.group(1) + "\n".join(kept) + match.group(3)
    return re.sub(r"(<meta>\n?)(.*?)(\n?</meta>)", clean, body, flags=re.S)


def norm_text(s: str) -> str:
    """Whitespace- and case-normalized text used to compare quotes."""
    return " ".join(str(s).split()).casefold()


def derive_recommendation(scores: dict, core_ids) -> str:
    """Pedagogical rule of the simulator (design D7): fail | insufficient_signal | pass."""
    core = set(core_ids)
    core_scores = [scores.get(c, "no_evidence") for c in core]
    others = [s for c, s in scores.items() if c not in core]
    if "SN" in core_scores or core_scores.count("N") >= 2:
        return "fail"
    if "no_evidence" in core_scores:
        return "insufficient_signal"
    if "SN" in others or others.count("N") > 1:
        return "fail"
    return "pass"
