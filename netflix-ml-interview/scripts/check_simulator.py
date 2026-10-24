#!/usr/bin/env python3
"""Validate the Netflix ML interview simulator content (stdlib only).

Usage:
  check_simulator.py                    run every check
  check_simulator.py --stage coding     only per-stage checks for one stage (plus the catalog)
  check_simulator.py --only rubric      run a single check (see --list)
  check_simulator.py --root <repo>      validate another checkout (used by tests)

Exit status: 0 when no errors, 1 otherwise. Missing optional dependencies (numpy/pandas)
skip the affected problem with a warning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import _content as content  # noqa: E402
import _testrun  # noqa: E402
import _yamlish as yamlish  # noqa: E402

STAGES = ["recruiter-screen", "hm-screen", "technical-screen", "presentation", "coding",
          "ai-assisted-coding", "ml-fundamentals", "ml-system-design", "experimentation",
          "culture", "ml-depth", "project-deep-dive", "partnership", "hm-onsite"]
PHASES = ("screen", "vo1", "vo2")
STYLES = ("conversational", "concise", "incisive")
WEIGHTS = ("high", "normal", "low")
ROLES = content.ROLES
SESSIONS_ENTRY = "netflix-ml-interview/sessions/"
ALLOW = ["Bash(python netflix-ml-interview/scripts/sim.py:*)", "Bash(python3 netflix-ml-interview/scripts/sim.py:*)",
         "Bash(py netflix-ml-interview/scripts/sim.py:*)"]
BLACKLIST = ("good", "great", "strong", "solid", "excellent", "adequate", "decent", "appropriate", "sufficient",
             "nice", "impressive", "outstanding", "superb", "satisfactory", "reasonable", "proper")
FORBIDDEN_TOOLS = {"bash", "write", "edit", "multiedit", "notebookedit"}
OPUS_AGENTS = {"netflix-ml-system-design", "netflix-hm-onsite", "netflix-evaluator", "netflix-hm-debrief"}
EXTRA_AGENTS = ["netflix-evaluator", "netflix-hm-debrief", "netflix-ai-pair"]
PROBLEM_FILES = ("problem.md", "starter.py", "tests.py", "reference.py", "followups.md")
GIT_RE = re.compile(r"\bgit\s+(add|commit|push)\b", re.I)


class Report:
    """Collects grouped errors and warnings."""

    def __init__(self):
        self.errors: dict[str, list[str]] = {}
        self.warnings: list[str] = []
        self.ran: list[str] = []

    def err(self, check: str, where, msg: str) -> None:
        self.errors.setdefault(check, []).append(f"{where}: {msg}")

    def warn(self, check: str, msg: str) -> None:
        self.warnings.append(f"[{check}] {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors


class Env:
    def __init__(self, root: Path):
        self.root = root
        self.kb = root / "netflix-ml-interview"
        self.stages = self.kb / "stages"
        self.catalog = None

    def rel(self, p: Path) -> str:
        try:
            return p.relative_to(self.root).as_posix()
        except ValueError:
            return str(p)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def load_yaml_file(rep: Report, check: str, env: Env, path: Path):
    if not path.is_file():
        rep.err(check, env.rel(path), "file is missing")
        return None
    try:
        return yamlish.loads(read(path))
    except yamlish.YamlError as exc:
        rep.err(check, env.rel(path), f"invalid YAML subset: {exc}")
        return None


# --------------------------------------------------------------- repo files
def check_gitignore(env: Env, rep: Report, stage=None):
    path = env.root / ".gitignore"
    if not path.is_file():
        rep.err("gitignore", ".gitignore", f"missing; it must contain '{SESSIONS_ENTRY}'")
        return
    lines = {l.strip().lstrip("/") for l in read(path).splitlines()}
    if SESSIONS_ENTRY not in lines and SESSIONS_ENTRY.rstrip("/") not in lines:
        rep.err("gitignore", ".gitignore", f"missing entry '{SESSIONS_ENTRY}'")


def check_settings(env: Env, rep: Report, stage=None):
    path = env.root / ".claude" / "settings.json"
    if not path.is_file():
        rep.err("settings", ".claude/settings.json", "file is missing")
        return
    try:
        allow = json.loads(read(path)).get("permissions", {}).get("allow", [])
    except (ValueError, AttributeError) as exc:
        rep.err("settings", ".claude/settings.json", f"invalid JSON: {exc}")
        return
    for entry in ALLOW:
        if entry not in allow:
            rep.err("settings", ".claude/settings.json", f"permissions.allow lacks '{entry}'")


def check_skill(env: Env, rep: Report, stage=None):
    skill = env.root / ".claude" / "skills" / "netflix-ml-interview"
    if not skill.is_dir():
        rep.err("skill", env.rel(skill), "skill directory is missing")
        return
    files = [p for p in skill.rglob("*") if p.is_file() and p.suffix in (".md", ".yaml", ".yml", ".txt", ".json")]
    if not any(p.name == "SKILL.md" for p in files):
        rep.err("skill", env.rel(skill / "SKILL.md"), "file is missing")
    for p in files:
        for n, line in enumerate(read(p).splitlines(), 1):
            m = GIT_RE.search(line)
            if m:
                rep.err("skill", f"{env.rel(p)}:{n}", f"forbidden command '{m.group(0)}' (sessions must never be committed)")


# ------------------------------------------------------------------ catalog
def check_catalog(env: Env, rep: Report, stage=None):
    cat = load_yaml_file(rep, "catalog", env, env.kb / "catalog.yaml")
    if not isinstance(cat, dict):
        return
    env.catalog = cat
    where = "catalog.yaml"
    if not isinstance(cat.get("version"), int):
        rep.err("catalog", where, "version must be an integer")
    domains = cat.get("domains")
    if not (isinstance(domains, list) and domains and len(set(domains)) == len(domains)):
        rep.err("catalog", where, "domains must be a non-empty list without duplicates")
        domains = []
    stages = cat.get("stages") if isinstance(cat.get("stages"), list) else []
    ids = [s.get("id") for s in stages if isinstance(s, dict)]
    if sorted(ids) != sorted(STAGES):
        missing, extra = sorted(set(STAGES) - set(ids)), sorted(set(ids) - set(STAGES))
        rep.err("catalog", where, f"stages must be exactly the 14 catalog stages (missing={missing}, unexpected={extra})")
    if len(set(ids)) != len(ids):
        rep.err("catalog", where, "duplicate stage ids")
    orders = [s.get("order") for s in stages if isinstance(s, dict)]
    if len(set(orders)) != len(orders) or not all(isinstance(o, int) for o in orders):
        rep.err("catalog", where, "stage 'order' must be unique integers")
    for s in stages:
        if isinstance(s, dict):
            check_stage_entry(rep, s)
    roles = cat.get("roles") if isinstance(cat.get("roles"), dict) else {}
    if sorted(roles) != sorted(ROLES):
        rep.err("catalog", where, f"roles must be exactly {list(ROLES)}")
    for rid, role in roles.items():
        check_role_entry(rep, rid, role, {s["id"]: s for s in stages if isinstance(s, dict) and "id" in s}, domains)


def check_stage_entry(rep: Report, s: dict) -> None:
    sid = s.get("id")
    w = f"catalog.yaml stage {sid}"
    if s.get("default_phase") not in PHASES:
        rep.err("catalog", w, f"default_phase must be one of {PHASES}")
    if not isinstance(s.get("minutes"), int) or s["minutes"] <= 0:
        rep.err("catalog", w, "minutes must be a positive integer")
    persona = s.get("persona") if isinstance(s.get("persona"), dict) else {}
    for k in ("name", "title", "style"):
        if not persona.get(k):
            rep.err("catalog", w, f"persona.{k} is missing")
    if persona.get("style") and persona["style"] not in STYLES:
        rep.err("catalog", w, f"persona.style must be one of {STYLES}")
    if s.get("agent") != f"netflix-{sid}":
        rep.err("catalog", w, f"agent must be 'netflix-{sid}'")
    variants = s.get("variants")
    if not isinstance(variants, list):
        rep.err("catalog", w, "variants must be a list (use [] when the stage has none)")
        variants = []
    vids = []
    for v in variants:
        if not (isinstance(v, dict) and v.get("id") and isinstance(v.get("roles"), list) and v["roles"]
                and set(v["roles"]) <= set(ROLES)):
            rep.err("catalog", w, f"variant {v!r} needs id and roles (subset of {list(ROLES)})")
            continue
        vids.append(v["id"])
        if "minutes" in v and not (isinstance(v["minutes"], int) and v["minutes"] > 0):
            rep.err("catalog", w, f"variant {v['id']}: minutes must be a positive integer")
        if "materials" in v and not (isinstance(v["materials"], list) and all(isinstance(m, str) for m in v["materials"])):
            rep.err("catalog", w, f"variant {v['id']}: materials must be a list of directory names")
    if len(set(vids)) != len(vids):
        rep.err("catalog", w, "duplicate variant ids")
    check_variant_by_role(rep, w, s, variants)
    comps = s.get("competencies") if isinstance(s.get("competencies"), list) else []
    cids = [c.get("id") for c in comps if isinstance(c, dict)]
    if not 3 <= len(comps) <= 6:
        rep.err("catalog", w, f"needs 3-6 competencies, found {len(comps)}")
    if len(set(cids)) != len(cids):
        rep.err("catalog", w, "duplicate competency ids")
    if not all(isinstance(c, dict) and re.match(r"^[a-z][a-z0-9_]*$", str(c.get("id", ""))) and isinstance(c.get("core"), bool) for c in comps):
        rep.err("catalog", w, "each competency needs a snake_case id and boolean core")
    elif not any(c["core"] for c in comps):
        rep.err("catalog", w, "at least one competency must be core")
    if not any(str(c).startswith("culture") for c in cids):
        rep.err("catalog", w, "needs a culture competency (id starting with 'culture')")


def check_variant_by_role(rep: Report, w: str, s: dict, variants: list) -> None:
    vbr = s.get("variant_by_role")
    if not variants:
        if vbr:
            rep.err("catalog", w, "variant_by_role must be absent when the stage has no variants")
        return
    if not isinstance(vbr, dict) or sorted(vbr) != sorted(ROLES):
        rep.err("catalog", w, f"variant_by_role must define {list(ROLES)}")
        return
    by_id = {v["id"]: v for v in variants if isinstance(v, dict) and "id" in v}
    for role, vid in vbr.items():
        if vid not in by_id or role not in by_id[vid].get("roles", []):
            rep.err("catalog", w, f"variant_by_role.{role}='{vid}' is not a variant compatible with {role}")


def check_role_entry(rep: Report, rid: str, role, stages: dict, domains: list) -> None:
    w = f"catalog.yaml role {rid}"
    if not isinstance(role, dict):
        rep.err("catalog", w, "must be a map")
        return
    if not role.get("label"):
        rep.err("catalog", w, "label is missing")
    if not isinstance(role.get("cut"), bool):
        rep.err("catalog", w, "cut must be true/false")
    if role.get("default_domain") not in domains:
        rep.err("catalog", w, "default_domain must be one of the domains")
    loop = role.get("loop") if isinstance(role.get("loop"), dict) else {}
    if sorted(loop) != sorted(PHASES):
        rep.err("catalog", w, f"loop must define {list(PHASES)}")
    weights = role.get("weights") if isinstance(role.get("weights"), dict) else {}
    for key, val in weights.items():
        st, _, var = str(key).partition("@")
        if val not in WEIGHTS:
            rep.err("catalog", w, f"weight of '{key}' must be one of {WEIGHTS}")
        if st not in stages or (var and var not in [v["id"] for v in stages[st].get("variants", []) if isinstance(v, dict) and "id" in v]):
            rep.err("catalog", w, f"weights key '{key}' does not match any stage/variant")
    for ph in PHASES:
        for entry in loop.get(ph) or []:
            check_loop_entry(rep, w, rid, ph, str(entry), stages, weights)


def check_loop_entry(rep: Report, w: str, rid: str, phase: str, entry: str, stages: dict, weights: dict) -> None:
    stage, _, variant = entry.partition("@")
    st = stages.get(stage)
    if st is None:
        rep.err("catalog", w, f"loop {phase}: unknown stage '{entry}'")
        return
    vlist = [v for v in st.get("variants", []) if isinstance(v, dict)]
    if variant:
        vd = next((v for v in vlist if v.get("id") == variant), None)
        if vd is None:
            rep.err("catalog", w, f"loop {phase}: '{entry}' names a variant that does not exist")
        elif rid not in vd.get("roles", []):
            rep.err("catalog", w, f"loop {phase}: variant '{entry}' is not compatible with role {rid}")
    elif vlist:
        rep.err("catalog", w, f"loop {phase}: '{entry}' must name a variant (stage@variant)")
    if f"{stage}@{variant}" not in weights and stage not in weights:
        rep.err("catalog", w, f"loop {phase}: '{entry}' has no weight (add '{stage}' or '{stage}@{variant}' to weights)")


# ------------------------------------------------------------ catalog views
def stage_list(env: Env, only):
    if not env.catalog:
        return []
    out = [s for s in env.catalog.get("stages", []) if isinstance(s, dict) and "id" in s]
    return [s for s in out if only in (None, s["id"])]


def applicable_roles(env: Env, stage: dict, variant: str | None) -> list[str]:
    """Roles that must have content for a stage/variant."""
    if variant:
        vd = next((v for v in stage.get("variants", []) if v.get("id") == variant), {})
        return [r for r in ROLES if r in vd.get("roles", [])]
    roles = []
    for rid, role in (env.catalog.get("roles") or {}).items():
        loop = role.get("loop") or {}
        if any(str(e).partition("@")[0] == stage["id"] for ph in PHASES for e in loop.get(ph) or []):
            roles.append(rid)
    return roles or list(ROLES)


# ------------------------------------------------------------- stage files
def check_briefs(env: Env, rep: Report, stage=None):
    for st in stage_list(env, stage):
        path = env.stages / st["id"] / "brief.md"
        if not path.is_file():
            rep.err("brief", env.rel(path), "brief.md is missing")
            continue
        text = read(path)
        m = re.search(r"^#{1,4}\s*Sources?\b.*$", text, re.M | re.I)
        if not m or not re.search(r"^\s*[-*]\s+\S", text[m.end():], re.M):
            rep.err("brief", env.rel(path), "needs a 'Sources' heading followed by at least one bullet")


def check_questions(env: Env, rep: Report, stage=None):
    domains = (env.catalog or {}).get("domains") or []
    for st in stage_list(env, stage):
        path = env.stages / st["id"] / "questions.md"
        if not path.is_file():
            rep.err("questions", env.rel(path), "questions.md is missing")
            continue
        items = content.parse_questions(read(path))
        seen = set()
        for q in items:
            validate_question(rep, env, path, q, st, domains, seen)
        require_min_main(env, rep, st, path, items)


def validate_question(rep, env, path, q, st, domains, seen) -> None:
    w = f"{env.rel(path)} ### {q['id']}"
    if q["id"] in seen:
        rep.err("questions", w, "duplicate question id")
    seen.add(q["id"])
    if q["error"]:
        rep.err("questions", w, q["error"])
        return
    m = q["meta"]
    if not set(m.get("roles") or []) <= set(ROLES) or not m.get("roles"):
        rep.err("questions", w, f"roles must be a non-empty subset of {list(ROLES)}")
    if not set(m.get("levels") or []) <= set(content.LEVELS) or not m.get("levels"):
        rep.err("questions", w, f"levels must be a non-empty subset of {list(content.LEVELS)}")
    vids = [v["id"] for v in st.get("variants", [])]
    variant = content.variant_of(m)
    if (vids and variant not in vids) or (not vids and variant != "default"):
        rep.err("questions", w, f"variant '{m.get('variant')}' invalid; valid: {vids or ['default (or omit)']}")
    if m.get("domain") not in ["any", *domains]:
        rep.err("questions", w, f"domain must be 'any' or one of {domains}")
    if m.get("kind") not in content.QUESTION_KINDS:
        rep.err("questions", w, f"kind must be one of {content.QUESTION_KINDS}")
    if m.get("kind") == "main" and not (isinstance(m.get("signal_points"), list) and m["signal_points"]):
        rep.err("questions", w, "main questions need signal_points[]")
    if not q["body"]:
        rep.err("questions", w, "statement text is empty")


def count_items(env: Env, st: dict, items: list, role: str, variant: str | None) -> int:
    key = variant or "default"
    n = sum(1 for q in items if not q["error"] and q["meta"].get("kind") == "main"
            and role in (q["meta"].get("roles") or []) and content.variant_of(q["meta"]) == key)
    for d in ("problems",):
        base = env.stages / st["id"] / d
        if base.is_dir():
            for p in base.iterdir():
                meta = problem_meta(p)
                if meta is not None and role in (meta.get("roles") or []) and content.variant_of(meta) == key:
                    n += 1
    return n


def problem_meta(p: Path):
    f = p / "problem.md"
    if not (p.is_dir() and f.is_file()):
        return None
    try:
        return yamlish.split_front_matter(read(f))[0]
    except yamlish.YamlError:
        return {}


def require_min_main(env, rep, st, path, items) -> None:
    variants = [v["id"] for v in st.get("variants", [])] or [None]
    for v in variants:
        for role in applicable_roles(env, st, v):
            n = count_items(env, st, items, role, v)
            if n < 2:
                rep.err("questions", env.rel(path), f"needs >= 2 'main' questions (or problems) for role={role} variant={v or 'default'}, found {n}")


def check_rubrics(env: Env, rep: Report, stage=None):
    for st in stage_list(env, stage):
        path = env.stages / st["id"] / "rubric.md"
        if not path.is_file():
            rep.err("rubric", env.rel(path), "rubric.md is missing")
            continue
        try:
            rub = content.parse_rubric(read(path))
        except yamlish.YamlError as exc:
            rep.err("rubric", env.rel(path), f"invalid front matter: {exc}")
            continue
        validate_rubric(rep, env.rel(path), st, rub)


def validate_rubric(rep: Report, w: str, st: dict, rub: dict) -> None:
    front = rub["front"]
    if front.get("stage") != st["id"]:
        rep.err("rubric", w, f"front matter stage must be '{st['id']}'")
    if front.get("rubric_version") in (None, ""):
        rep.err("rubric", w, "front matter needs rubric_version")
    shared = rub["shared"]
    for term in ("Strong No", "Strong Yes"):
        if term not in shared:
            rep.err("rubric", w, f"shared section must define '{term}'")
    if not re.search(r"\bNo\b", shared):
        rep.err("rubric", w, "shared section must define 'No'")
    comps = rub["competencies"]
    ids = [c["id"] for c in comps]
    if not 3 <= len(comps) <= 6:
        rep.err("rubric", w, f"needs 3-6 competencies, found {len(comps)}")
    if len(set(ids)) != len(ids):
        rep.err("rubric", w, "duplicate competency ids")
    if comps and not any(c["core"] for c in comps):
        rep.err("rubric", w, "at least one competency must be core")
    catalog = {c["id"]: c["core"] for c in st.get("competencies", [])}
    if set(ids) != set(catalog):
        rep.err("rubric", w, f"competency ids differ from the catalog (missing={sorted(set(catalog) - set(ids))}, unexpected={sorted(set(ids) - set(catalog))})")
    for c in comps:
        validate_competency(rep, w, c, catalog)
    if comps and not any(c["id"].startswith("culture") for c in comps):
        rep.err("rubric", w, "needs a culture competency")


def validate_competency(rep: Report, w: str, c: dict, catalog: dict) -> None:
    cw = f"{w} ## {c['id']}"
    if c["id"] in catalog and catalog[c["id"]] != c["core"]:
        rep.err("rubric", cw, f"core={c['core']} differs from the catalog ({catalog[c['id']]})")
    if c["id"].startswith("culture"):
        vals = c["memo_values"]
        if not vals or not set(vals) <= set(content.MEMO_VALUES):
            rep.err("rubric", cw, f"culture competency needs memo_values (subset of {list(content.MEMO_VALUES)})")
    bars = c["levels"]
    missing = [l for l in content.LEVELS if not bars.get(l)]
    if missing:
        rep.err("rubric", cw, f"Yes-bar table lacks levels {missing}")
        return
    if len({content.norm_text(bars[l]) for l in content.LEVELS}) < 3:
        rep.err("rubric", cw, "L4/L5/L6 bars must differ from each other")
    for lvl in content.LEVELS:
        words = [b for b in BLACKLIST if re.search(rf"\b{b}\b", bars[lvl], re.I)]
        if words:
            rep.err("rubric", cw, f"{lvl} bar uses vague adjectives {words}; describe observable behavior")


# ------------------------------------------------------------------- agents
def parse_agent(text: str):
    """Tolerant front-matter parser: 'key: value' lines (values may contain colons)."""
    m = re.match(r"^---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    if not m:
        return None
    data, key = {}, None
    for line in m.group(1).split("\n"):
        kv = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if kv:
            key = kv.group(1)
            data[key] = kv.group(2).strip()
        elif key and line.strip().startswith("- "):
            data[key] = (data[key] + "," if data[key] else "") + line.strip()[2:]
    return data


def agent_names(env: Env, stage) -> list[str]:
    if stage:
        return [f"netflix-{stage}"]
    return [f"netflix-{s}" for s in STAGES] + EXTRA_AGENTS


def check_agents(env: Env, rep: Report, stage=None):
    adir = env.root / ".claude" / "agents"
    for name in agent_names(env, stage):
        path = adir / f"{name}.md"
        w = env.rel(path)
        if not path.is_file():
            rep.err("agents", w, "agent file is missing")
            continue
        fm = parse_agent(read(path))
        if fm is None:
            rep.err("agents", w, "missing front matter")
            continue
        if fm.get("name") != name:
            rep.err("agents", w, f"name '{fm.get('name')}' must equal the file name '{name}'")
        if not fm.get("description"):
            rep.err("agents", w, "description is missing")
        tools = [t.strip().strip("[]\"'") for t in re.split(r"[,\s]+", fm.get("tools", "")) if t.strip().strip("[]\"'")]
        bad = [t for t in tools if t.lower() in FORBIDDEN_TOOLS]
        if not tools:
            rep.err("agents", w, "tools must be declared (Read, Glob, Grep)")
        if bad:
            rep.err("agents", w, f"forbidden tools {bad} (agents have no Bash/Write)")
        want = "opus" if name in OPUS_AGENTS else "sonnet"
        if want not in fm.get("model", "").lower():
            rep.err("agents", w, f"model must be {want} (found '{fm.get('model')}')")
    if not stage and adir.is_dir():
        known = set(agent_names(env, None))
        for p in adir.glob("netflix-*.md"):
            if p.stem not in known:
                rep.err("agents", env.rel(p), "unexpected agent (the design defines exactly 17)")


# ---------------------------------------------------------------- study map
def check_studymap(env: Env, rep: Report, stage=None):
    path = env.kb / "study-map.yaml"
    data = load_yaml_file(rep, "studymap", env, path)
    if not isinstance(data, dict) or not env.catalog:
        return
    wanted = {f"{s['id']}.{c['id']}" for s in stage_list(env, stage) for c in s.get("competencies", [])}
    for key in sorted(wanted - set(data)):
        rep.err("studymap", env.rel(path), f"no entry for '{key}'")
    for key, entry in data.items():
        st, _, comp = key.partition(".")
        if stage and st != stage:
            continue
        if key not in {f"{s['id']}.{c['id']}" for s in env.catalog.get("stages", []) for c in s.get("competencies", [])}:
            rep.err("studymap", f"{env.rel(path)} {key}", "unknown <stage>.<competency_id>")
            continue
        validate_study_entry(env, rep, f"{env.rel(path)} {key}", entry)


def validate_study_entry(env: Env, rep: Report, w: str, entry) -> None:
    if not isinstance(entry, dict):
        rep.err("studymap", w, "entry must be a map")
        return
    courses = entry.get("course") or []
    if not (courses or entry.get("practice_stage") or entry.get("resource")):
        rep.err("studymap", w, "needs course[], practice_stage or resource")
    for c in courses:
        if not (env.root / str(c)).is_dir():
            rep.err("studymap", w, f"course path does not exist: {c}")
    ps = entry.get("practice_stage")
    if ps and ps not in STAGES:
        rep.err("studymap", w, f"practice_stage '{ps}' is not a stage")


# ------------------------------------------------------- sources/templates
def check_sources(env: Env, rep: Report, stage=None):
    path = env.kb / "sources.md"
    if not path.is_file():
        rep.err("sources", env.rel(path), "sources.md is missing")
        return
    text = read(path)
    for sid in ([stage] if stage else STAGES):
        m = re.search(rf"^##\s+{re.escape(sid)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
        if not m:
            rep.err("sources", env.rel(path), f"no '## {sid}' section")
            continue
        body = m.group(1)
        if not re.search(r"confidence:\s*(high|medium|low)", body, re.I):
            rep.err("sources", f"{env.rel(path)} ## {sid}", "needs 'Confidence: High|Medium|Low'")
        if not re.search(r"duration[^\n]*assumption", body, re.I):
            rep.err("sources", f"{env.rel(path)} ## {sid}", "needs a 'Duration' line flagged as an assumption")


def check_templates(env: Env, rep: Report, stage=None):
    tdir = env.kb / "templates"
    sess = load_yaml_file(rep, "templates", env, tdir / "session.yaml")
    if isinstance(sess, dict):
        need = ("id", "created", "role", "level", "lang", "domain", "time_scale", "python", "env_ephemeral", "feedback", "mode", "instances")
        for k in need:
            if k not in sess:
                rep.err("templates", "templates/session.yaml", f"missing key '{k}'")
    for name, keys in (("scorecard.md", ("instance_id", "stage", "variant", "level", "rubric_version", "recommendation", "level_observed", "scores", "evidence", "hints")),
                       ("debrief.md", ("type", "provisional_outcome", "outcome", "level", "override"))):
        p = tdir / name
        if not p.is_file():
            rep.err("templates", env.rel(p), "file is missing")
            continue
        try:
            front, body = yamlish.split_front_matter(read(p))
        except yamlish.YamlError as exc:
            rep.err("templates", env.rel(p), f"invalid front matter: {exc}")
            continue
        for k in keys:
            if k not in front:
                rep.err("templates", env.rel(p), f"front matter lacks '{k}'")
        if "pedagogical rule" not in body or "regla pedag" not in body:
            rep.err("templates", env.rel(p), "must carry the pedagogical-rule note in English and Spanish")


# ---------------------------------------------------- executable materials
def has_modules(names: list[str]) -> list[str]:
    import importlib.util
    return [n for n in names if importlib.util.find_spec(n) is None]


def requires_of(meta: dict) -> list[str]:
    req = meta.get("requires") or []
    return [str(r) for r in req] if isinstance(req, list) else [str(req)]


def check_problems(env: Env, rep: Report, stage=None):
    for st in stage_list(env, stage):
        base = env.stages / st["id"] / "problems"
        if base.is_dir():
            for p in sorted(x for x in base.iterdir() if x.is_dir() and not x.name.startswith(".")):
                check_problem(env, rep, st, p)


def check_problem(env: Env, rep: Report, st: dict, p: Path) -> None:
    w = env.rel(p)
    for f in PROBLEM_FILES:
        if not (p / f).is_file():
            rep.err("coding", w, f"missing {f}")
    meta = problem_meta(p)
    if meta is None or not (p / "tests.py").is_file() or not (p / "reference.py").is_file():
        return
    vids = [v["id"] for v in st.get("variants", [])]
    if content.variant_of(meta) not in vids:
        rep.err("coding", w, f"problem.md front matter variant '{meta.get('variant')}' must be one of {vids}")
    if not set(meta.get("roles") or []) <= set(ROLES) or not meta.get("roles"):
        rep.err("coding", w, "problem.md front matter needs roles[]")
    if not set(meta.get("levels") or []) <= set(content.LEVELS) or not meta.get("levels"):
        rep.err("coding", w, "problem.md front matter needs levels[]")
    if (p / "followups.md").is_file() and not re.search(r"scale|concurren|thread|parallel", read(p / "followups.md"), re.I):
        rep.err("coding", w, "followups.md must cover scale and concurrency")
    missing = has_modules(requires_of(meta))
    if missing:
        rep.warn("coding", f"{w}: skipped tests, missing modules {missing} (pip install -r netflix-ml-interview/requirements.txt)")
        return
    res = _testrun.run_in_scratch({"tests.py": p / "tests.py", "solution.py": p / "reference.py"}, base=p,
                                  timeout=120, mode="module", target="tests")
    report_test_result(rep, "coding", w, res, "reference.py does not pass tests.py")


def report_test_result(rep: Report, check: str, w: str, res: dict, label: str) -> None:
    if res["error"]:
        if re.search(r"No module named '(numpy|pandas)'", res["error"]):
            rep.warn(check, f"{w}: skipped, dependency missing ({res['error'].strip().splitlines()[-1]})")
        else:
            rep.err(check, w, f"{label}: {res['error'].strip().splitlines()[-1][:200]}")
    elif res["total"] == 0:
        rep.err(check, w, f"{label}: no tests were collected")
    elif res["failing"]:
        rep.err(check, w, f"{label}: failing {res['failing']}")


def check_ai_repos(env: Env, rep: Report, stage=None):
    if stage not in (None, "ai-assisted-coding"):
        return
    base = env.stages / "ai-assisted-coding" / "repos"
    repos = sorted(x for x in base.iterdir() if x.is_dir() and not x.name.startswith(".")) if base.is_dir() else []
    if not repos:
        rep.err("aicoding", env.rel(base), "no repos found (need at least 3, with 0, 1 and 2 flaws)")
        return
    if len(repos) < 3:
        rep.warn("aicoding", f"only {len(repos)} repos; the plan asks for at least 3")
    counts = set()
    for r in repos:
        counts.add(check_ai_repo(env, rep, r))
    if len(repos) >= 3 and not {0, 1, 2} <= counts:
        rep.warn("aicoding", f"repos should cover 0, 1 and 2 flaws (found counts {sorted(c for c in counts if c is not None)})")


def check_ai_repo(env: Env, rep: Report, r: Path):
    w = env.rel(r)
    for f in ("tasks.md", "notes.md", "flaws.yaml"):
        if not (r / f).is_file():
            rep.err("aicoding", w, f"missing {f}")
    ws = r / "workspace"
    if not ws.is_dir():
        rep.err("aicoding", w, "missing workspace/")
        return None
    res = _testrun.run_in_scratch({}, base=ws, timeout=120)
    report_test_result(rep, "aicoding", w + "/workspace", res, "workspace tests must be green")
    if not (r / "flaws.yaml").is_file():
        return None
    data = load_yaml_file(rep, "aicoding", env, r / "flaws.yaml")
    flaws = (data or {}).get("flaws") if isinstance(data, dict) else None
    if not isinstance(flaws, list):
        rep.err("aicoding", w + "/flaws.yaml", "needs a 'flaws' list (use [] for none)")
        return None
    if len(flaws) > 2:
        rep.err("aicoding", w + "/flaws.yaml", "at most 2 flaws per repo")
    for fl in flaws:
        check_flaw(env, rep, r, ws, fl)
    return len(flaws)


def check_flaw(env: Env, rep: Report, r: Path, ws: Path, fl) -> None:
    w = f"{env.rel(r)}/flaws.yaml flaw {fl.get('id') if isinstance(fl, dict) else fl}"
    if not isinstance(fl, dict):
        rep.err("aicoding", w, "flaw must be a map")
        return
    for k in ("id", "zone", "description", "hidden_test"):
        if not fl.get(k):
            rep.err("aicoding", w, f"missing {k}")
    if not (isinstance(fl.get("trigger_keywords"), list) and fl["trigger_keywords"]):
        rep.err("aicoding", w, "trigger_keywords[] must be non-empty")
    src = r / str(fl.get("hidden_test", ""))
    if not fl.get("hidden_test") or not src.is_file():
        rep.err("aicoding", w, f"hidden_test file not found: {fl.get('hidden_test')}")
        return
    mod = "hidden_" + re.sub(r"\W", "_", str(fl["id"]))
    res = _testrun.run_in_scratch({mod + ".py": src}, base=ws, timeout=120, mode="module", target=mod)
    report_test_result(rep, "aicoding", w, res, "hidden_test must pass on the clean workspace")


def check_takehomes(env: Env, rep: Report, stage=None):
    if stage not in (None, "presentation"):
        return
    base = env.stages / "presentation" / "takehomes"
    items = sorted(x for x in base.iterdir() if x.is_dir() and not x.name.startswith(".")) if base.is_dir() else []
    if not items:
        rep.err("takehomes", env.rel(base), "no take-homes found (need at least 2)")
        return
    if len(items) < 2:
        rep.warn("takehomes", "fewer than 2 take-homes")
    for t in items:
        check_takehome(env, rep, t)


def digest_dir(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}


def check_takehome(env: Env, rep: Report, t: Path) -> None:
    w = env.rel(t)
    for f in ("prompt.md", "generate_data.py"):
        if not (t / f).is_file():
            rep.err("takehomes", w, f"missing {f}")
    gen = t / "generate_data.py"
    if not gen.is_file():
        return
    if not re.search(r"seed", read(gen), re.I):
        rep.err("takehomes", w, "generate_data.py must seed its random generators")
    meta = yamlish.split_front_matter(read(t / "prompt.md"))[0] if (t / "prompt.md").is_file() else {}
    missing = has_modules(requires_of(meta))
    if missing:
        rep.warn("takehomes", f"{w}: skipped determinism check, missing modules {missing}")
        return
    runs = []
    for _ in range(2):
        with tempfile.TemporaryDirectory(prefix="sim-takehome-") as tmp:
            proc = subprocess.run([sys.executable, str(gen), tmp], cwd=tmp, capture_output=True, text=True, timeout=300)
            if proc.returncode != 0:
                tail = (proc.stderr or "").strip().splitlines()[-1:] or ["failed"]
                if "No module named" in tail[0]:
                    rep.warn("takehomes", f"{w}: skipped, dependency missing ({tail[0]})")
                else:
                    rep.err("takehomes", w, f"generate_data.py failed: {tail[0][:200]}")
                return
            runs.append(digest_dir(Path(tmp)))
    if runs[0] != runs[1]:
        rep.err("takehomes", w, "generate_data.py is not deterministic (two runs differ)")
    elif not runs[0]:
        rep.err("takehomes", w, "generate_data.py wrote no files into the output directory (argv[1])")


def check_sql(env: Env, rep: Report, stage=None):
    for st in stage_list(env, stage):
        base = env.stages / st["id"] / "datasets"
        for f in sorted(base.glob("*.sql")) if base.is_dir() else []:
            con = sqlite3.connect(":memory:")
            try:
                con.executescript(read(f))
            except sqlite3.Error as exc:
                rep.err("sql", env.rel(f), f"does not run on sqlite3: {exc}")
            finally:
                con.close()


def check_materials(env: Env, rep: Report, stage=None):
    for st in stage_list(env, stage):
        for v in st.get("variants", []):
            for m in v.get("materials", []) or []:
                d = env.stages / st["id"] / m
                if not d.is_dir() or not any(not x.name.startswith(".") for x in d.iterdir()):
                    rep.err("materials", env.rel(d), f"variant {st['id']}@{v['id']} declares materials '{m}' but the directory is missing or empty")


# --------------------------------------------------------------------- main
GLOBAL = {"gitignore": check_gitignore, "settings": check_settings, "skill": check_skill, "studymap": check_studymap,
          "templates": check_templates, "agents": check_agents, "sources": check_sources}
PER_STAGE = {"brief": check_briefs, "questions": check_questions, "rubric": check_rubrics, "materials": check_materials,
             "coding": check_problems, "aicoding": check_ai_repos, "takehomes": check_takehomes, "sql": check_sql}
ALL = {"catalog": check_catalog, **GLOBAL, **PER_STAGE}
STAGE_AWARE = {"agents", "studymap", "sources"}


def run(env: Env, only=None, stage=None) -> Report:
    """Run the selected checks; the catalog is always loaded because most checks need it."""
    rep = Report()
    if only:
        names = [only]
    else:
        names = ["catalog", *PER_STAGE, *[g for g in GLOBAL if not stage or g in STAGE_AWARE]]
    if "catalog" not in names:
        check_catalog(env, Report())
    for name in names:
        rep.ran.append(name)
        ALL[name](env, rep, stage)
    return rep


def render(rep: Report) -> str:
    lines = []
    for check in rep.ran:
        errs = rep.errors.get(check, [])
        lines.append(f"[{'FAIL' if errs else 'ok'}] {check}" + (f" ({len(errs)})" if errs else ""))
        lines += [f"    - {e}" for e in errs]
    lines += [f"warning {w}" for w in rep.warnings]
    total = sum(len(v) for v in rep.errors.values())
    lines.append(f"\n{total} error(s) in {len(rep.errors)} check(s); {len(rep.warnings)} warning(s)")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(SCRIPT_DIR.parent.parent), help="repository root")
    ap.add_argument("--only", choices=sorted(ALL), help="run a single check")
    ap.add_argument("--stage", choices=STAGES, help="restrict per-stage checks to one stage")
    ap.add_argument("--list", action="store_true", help="list check names")
    args = ap.parse_args(argv)
    if args.list:
        print("\n".join(sorted(ALL)))
        return 0
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    rep = run(Env(Path(args.root).resolve()), args.only, args.stage)
    print(render(rep))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
