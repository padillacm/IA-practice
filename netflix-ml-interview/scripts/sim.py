#!/usr/bin/env python3
"""Netflix ML interview simulator helper (stdlib only, Windows-portable).

All deterministic work lives here: sessions, active time, question selection, tests,
quote verification, the git guard, rebuild prompts and progress. Options such as
--json, --base and --now go AFTER the subcommand. Run `sim.py <cmd> -h` for details.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import _content as content  # noqa: E402
import _patch  # noqa: E402
import _testrun  # noqa: E402
import _yamlish as yamlish  # noqa: E402

PHASES = ("screen", "vo1", "vo2")
PHASE_ALIASES = {"screen": "screen", "screens": "screen", "vo1": "vo1", "vo2": "vo2"}
FULL_ALIASES = ("full", "loop", "all")
LEVELS = content.LEVELS
LANGS = {"en": "English", "es": "Spanish"}
FEEDBACK = ("immediate", "deferred")
MODES = ("normal", "practice", "degraded")
STATUSES = ("pending", "in_progress", "done", "skipped")
END_REASONS = {"completed": "candidate", "time_up": "candidate", "uncovered": "candidate",
               "candidate_end": "external", "interrupted": "external", "skipped": "external"}
FLAGS = ((100, "[time:100% — close the stage now]"),
         (90, "[time:90% — move to candidate questions]"),
         (80, "[time:80% — give the time warning now]"))
IDLE_CAP_MINUTES = 30
MATERIAL_DIRS = ("problems", "repos", "prs", "takehomes", "datasets")
INSTANCE_KEYS = ("status", "end_reason", "scorecard", "agent_name", "attempt", "question_ids",
                 "problem_id", "phase")
SESSION_KEYS = ("feedback", "mode", "background_path", "candidate_profile", "cut", "final",
                "python", "time_scale", "level", "lang", "domain")
TURN_CONTRACT = ("Each turn you MUST end with a final message containing exactly one `<say>…</say>` "
                 "followed by one `<meta>…</meta>` and nothing after. Never write or guess the candidate's "
                 "reply. Never call tools after writing `<say>`. Read files only on your first turn; later "
                 "turns are pure conversation. Reply as your final message, never via SendMessage.")
VARIABILITY = ("The simulated loop is an approximation: real Netflix loops vary by team and level. "
               "Confirm the actual structure with your recruiter.")
EPHEMERAL = ("Ephemeral environment detected (CLAUDE_CODE_REMOTE=true): local session history is lost "
             "when the container is recycled.")
SCORECARD_NOTE_EN = ("Recommendation derived by the simulator's pedagogical rule; "
                     "Netflix does not use a common scale.")


class SimError(Exception):
    """A user-facing error; ``code`` becomes the process exit status."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


class Ctx:
    """Execution context: knowledge-base dir, clock override and caches."""

    def __init__(self, base=None, now=None):
        self.base = Path(base).resolve() if base else SCRIPT_DIR.parent
        self._now = parse_iso(now) if now else None
        self.sessions = self.base / "sessions"
        self.stages = self.base / "stages"
        self.guard_result = None
        self.idle_cap = timedelta(minutes=IDLE_CAP_MINUTES)

    def now(self) -> datetime:
        return self._now or datetime.now(timezone.utc).replace(microsecond=0)


# ------------------------------------------------------------------ utils
def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    s = str(text).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def read_text(path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def emit(args, data, text: str) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False) if getattr(args, "json", False) else text)


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def input_text(args) -> str:
    """Text from --text, --file or --stdin."""
    if getattr(args, "text", None) is not None:
        return args.text
    if getattr(args, "file", None):
        return read_text(args.file)
    if getattr(args, "stdin", False):
        return sys.stdin.buffer.read().decode("utf-8", errors="replace").replace("\r\n", "\n")
    raise SimError("provide the text with --text, --file or --stdin")


def detect_python() -> str:
    for cmd in ("python", "python3", "py"):
        if shutil.which(cmd):
            return cmd
    return "python"


# ------------------------------------------------------------------ guard
def _git(args: list[str], cwd) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    except OSError:
        return None


def guard(ctx: Ctx) -> dict:
    """Design D8: sessions must be git-ignored and untracked before any write.

    status: ok | ok_no_repo | not_ignored | tracked | error
    """
    probe_dir = ctx.base if ctx.base.is_dir() else ctx.base.parent
    top = _git(["rev-parse", "--show-toplevel"], probe_dir)
    if top is None or top.returncode != 0:
        return {"ok": True, "status": "ok_no_repo",
                "message": "Not inside a git repository: nothing to protect, writing is allowed."}
    root = Path(top.stdout.strip()).resolve()
    try:
        rel = (ctx.sessions.resolve() if ctx.sessions.exists() else ctx.base.resolve() / "sessions").relative_to(root).as_posix()
    except ValueError:
        return {"ok": True, "status": "ok_no_repo", "message": "Sessions dir is outside the git repository."}
    chk = _git(["check-ignore", "-q", "--", f"{rel}/.probe"], root)
    if chk is None or chk.returncode not in (0, 1):
        code = "n/a" if chk is None else chk.returncode
        return {"ok": False, "status": "error",
                "message": f"git check-ignore failed (exit {code}): {(chk.stderr if chk else '').strip()}"}
    if chk.returncode == 1:
        return {"ok": False, "status": "not_ignored",
                "message": f"'{rel}/' is not git-ignored. Add the line '{rel}/' to the root .gitignore, then retry."}
    tracked = _git(["ls-files", "--", rel], root)
    if tracked is None or tracked.returncode != 0:
        return {"ok": False, "status": "error", "message": "git ls-files failed."}
    if tracked.stdout.strip():
        return {"ok": False, "status": "tracked",
                "message": f"Files under '{rel}/' are tracked by git. Untrack them yourself "
                           f"(git rm -r --cached {rel}) before using the simulator."}
    return {"ok": True, "status": "ok", "message": f"'{rel}/' is git-ignored and untracked."}


def ensure_writable(ctx: Ctx) -> None:
    """Every write goes through here."""
    if ctx.guard_result is None:
        ctx.guard_result = guard(ctx)
        if ctx.guard_result["status"] == "ok_no_repo":
            warn(ctx.guard_result["message"])
    if not ctx.guard_result["ok"]:
        raise SimError("guard refused to write: " + ctx.guard_result["message"], 1)
    ctx.sessions.mkdir(parents=True, exist_ok=True)


def cmd_guard(ctx: Ctx, args) -> int:
    res = guard(ctx)
    emit(args, res, f"{res['status']}: {res['message']}")
    return 0 if res["ok"] else (3 if res["status"] == "error" else 1)


# ---------------------------------------------------------------- catalog
def load_catalog(ctx: Ctx) -> dict:
    path = ctx.base / "catalog.yaml"
    if not path.is_file():
        raise SimError(f"catalog not found: {path}")
    return yamlish.loads(read_text(path))


def stage_def(cat: dict, stage: str) -> dict:
    for s in cat["stages"]:
        if s["id"] == stage:
            return s
    raise SimError(f"unknown stage '{stage}'. Valid: {', '.join(s['id'] for s in cat['stages'])}")


def variant_def(stage: dict, variant: str):
    return next((v for v in stage.get("variants") or [] if v["id"] == variant), None)


def budget_minutes(cat: dict, stage: str, variant: str) -> int:
    st = stage_def(cat, stage)
    v = variant_def(st, variant)
    return int((v or {}).get("minutes") or st["minutes"])


def default_variant(stage: dict, role: str) -> str:
    return (stage.get("variant_by_role") or {}).get(role, "default") if stage.get("variants") else "default"


def loop_entry(entry: str) -> tuple[str, str | None]:
    stage, _, variant = entry.partition("@")
    return stage, (variant or None)


def expand_stages(cat: dict, role: str, spec: str | None, order: str = "canonical") -> list[dict]:
    """Resolve a stages spec ('vo1', 'coding@practical,culture', 'full') into ordered entries."""
    tokens = [t.strip() for t in (spec or "full").split(",") if t.strip()] or ["full"]
    loop = cat["roles"][role]["loop"]
    stage_ids = [s["id"] for s in cat["stages"]]
    raw: list[tuple[str, str, str]] = []
    for tok in tokens:
        if tok in FULL_ALIASES:
            raw += [(*loop_entry(e), ph) for ph in PHASES for e in loop[ph]]
        elif tok in PHASE_ALIASES:
            ph = PHASE_ALIASES[tok]
            raw += [(*loop_entry(e), ph) for e in loop[ph]]
        else:
            stage, variant = loop_entry(tok)
            if stage not in stage_ids:
                raise SimError(f"unknown stage '{stage}'. Valid stages: {', '.join(stage_ids)}; "
                               f"phases: screen, vo1, vo2, full")
            raw.append((stage, variant, None))
    entries = []
    for seq, (stage, variant, phase) in enumerate(raw):
        entries.append(_finish_entry(cat, role, stage, variant, phase, seq))
    if order == "canonical":
        entries.sort(key=lambda e: (PHASES.index(e["phase"]), stage_def(cat, e["stage"])["order"], e["seq"]))
    return entries


def _finish_entry(cat, role, stage, variant, phase, seq) -> dict:
    st = stage_def(cat, stage)
    if variant is None:
        variant = default_variant(st, role)
    elif not st.get("variants"):
        raise SimError(f"stage '{stage}' has no variants (got '{stage}@{variant}')")
    else:
        vd = variant_def(st, variant)
        valid = [v["id"] for v in st["variants"] if role in v["roles"]]
        if vd is None or role not in vd["roles"]:
            raise SimError(f"invalid variant '{stage}@{variant}' for role '{role}'. Valid: "
                           + ", ".join(f"{stage}@{v}" for v in valid))
    if phase is None:
        phase = _phase_in_loop(cat, role, stage, variant) or st["default_phase"]
    return {"stage": stage, "variant": variant, "phase": phase, "seq": seq}


def _phase_in_loop(cat, role, stage, variant):
    loop = cat["roles"][role]["loop"]
    for ph in PHASES:
        for e in loop[ph]:
            s, v = loop_entry(e)
            if s == stage and (v or "default") == variant:
                return ph
    return None


def weight_for(cat: dict, role: str, stage: str, variant: str) -> str:
    w = cat["roles"][role].get("weights") or {}
    return w.get(f"{stage}@{variant}") or w.get(stage) or "normal"


# --------------------------------------------------------------- sessions
def agent_name(instance_id: str, session_id: str, attempt: int) -> str:
    """Agent name 'iv-<instance>-<session>-<attempt>' ('@' replaced to keep names hyphen-safe)."""
    return f"iv-{instance_id}-{session_id}-{attempt}".replace("@", "-")


def list_sessions(ctx: Ctx) -> list[tuple[Path, dict]]:
    out = []
    if ctx.sessions.is_dir():
        for d in sorted(ctx.sessions.iterdir()):
            f = d / "session.yaml"
            if d.is_dir() and f.is_file():
                try:
                    out.append((d, yamlish.loads(read_text(f)) or {}))
                except yamlish.YamlError as exc:
                    warn(f"{f}: {exc}")
    out.sort(key=lambda p: (str(p[1].get("created", "")), p[0].name))
    return out


def resolve_session(ctx: Ctx, ref: str) -> tuple[Path, dict]:
    sessions = list_sessions(ctx)
    if ref == "latest":
        if not sessions:
            raise SimError("no sessions found")
        return sessions[-1]
    direct = Path(ref)
    if (direct / "session.yaml").is_file():
        return direct, yamlish.loads(read_text(direct / "session.yaml"))
    hits = [s for s in sessions if s[0].name == ref or s[1].get("id") == ref]
    hits = hits or [s for s in sessions if s[0].name.endswith(ref) or s[0].name.startswith(ref)]
    if len(hits) != 1:
        raise SimError(f"session '{ref}' not found" if not hits else
                       f"session '{ref}' is ambiguous: {', '.join(h[0].name for h in hits)}")
    return hits[0]


def save_session(ctx: Ctx, sdir: Path, session: dict) -> None:
    ensure_writable(ctx)
    atomic_write(sdir / "session.yaml", yamlish.dumps(session))


def get_instance(session: dict, ref: str) -> dict:
    insts = session.get("instances") or []
    exact = [i for i in insts if i["instance_id"] == ref]
    hits = exact or [i for i in insts if i["instance_id"].startswith(ref + "-") or i["instance_id"].startswith(ref + "@")]
    if len(hits) != 1:
        valid = ", ".join(i["instance_id"] for i in insts)
        raise SimError(f"instance '{ref}' not found or ambiguous. Valid: {valid}")
    return hits[0]


def load_template(ctx: Ctx) -> dict:
    path = ctx.base / "templates" / "session.yaml"
    return yamlish.loads(read_text(path)) if path.is_file() else {}


def plan_new(ctx: Ctx, cat: dict, args) -> dict:
    """Validate the full configuration against the catalog and resolve the instances (no writes)."""
    errors = validate_new_args(cat, args)
    if errors:
        raise SimError("; ".join(errors))
    role = args.role
    entries = expand_stages(cat, role, args.stages, args.order)
    domain = args.domain or cat["roles"][role]["default_domain"]
    phases = {e["phase"] for e in entries}
    rows = [{"instance_id": f"{n:02d}-{e['stage']}@{e['variant']}", "stage": e["stage"], "variant": e["variant"],
             "phase": e["phase"], "minutes": budget_minutes(cat, e["stage"], e["variant"]),
             "weight": weight_for(cat, role, e["stage"], e["variant"])} for n, e in enumerate(entries, 1)]
    return {"role": role, "level": args.level, "lang": args.lang, "domain": domain, "feedback": args.feedback,
            "time_scale": float(args.time_scale), "background": str(args.background) if args.background else None,
            "entries": entries, "rows": rows, "cut": bool(cat["roles"][role]["cut"]),
            "cut_active": bool(cat["roles"][role]["cut"]) and {"vo1", "vo2"} <= phases}


def cmd_new(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    plan = plan_new(ctx, cat, args)
    role, entries = plan["role"], plan["entries"]
    warnings = [VARIABILITY] + ([EPHEMERAL] if os.environ.get("CLAUDE_CODE_REMOTE") == "true" else [])
    if args.dry_run:
        rows = [f"  {r['instance_id']}  [{r['phase']}]  {r['minutes']}m  weight={r['weight']}" for r in plan["rows"]]
        text = ("dry run: configuration is valid, nothing was created\n"
                f"role={role} level={plan['level']} lang={plan['lang']} domain={plan['domain']} "
                f"feedback={plan['feedback']} time_scale={plan['time_scale']}\n"
                f"cut between VO1 and VO2: {'on' if plan['cut_active'] else 'off'}"
                + ("" if plan["cut"] == plan["cut_active"] else " (role has a cut, but the selection lacks VO1 or VO2)")
                + f"\nbackground: {plan['background'] or 'none'}\ninstances:\n"
                + "\n".join(rows) + "\n" + "\n".join("warning: " + w for w in warnings))
        emit(args, {"dry_run": True, "valid": True, "config": {k: plan[k] for k in (
            "role", "level", "lang", "domain", "feedback", "time_scale", "background")},
            "instances": plan["rows"], "cut": plan["cut"], "cut_active": plan["cut_active"], "warnings": warnings}, text)
        return 0
    ensure_writable(ctx)
    now = ctx.now()
    sid = f"{now.strftime('%Y-%m-%d')}-{secrets.token_hex(3)}"
    session = load_template(ctx)
    session.update({"id": sid, "created": iso(now), "role": role, "level": args.level, "lang": args.lang,
                    "domain": plan["domain"],
                    "time_scale": float(args.time_scale), "python": args.python or detect_python(),
                    "env_ephemeral": os.environ.get("CLAUDE_CODE_REMOTE") == "true",
                    "feedback": args.feedback, "mode": "normal"})
    session.pop("background_path", None)
    session.pop("candidate_profile", None)
    session.pop("cut", None)
    session.pop("final", None)
    if args.background:
        session["background_path"] = str(args.background)
    session["instances"] = [new_instance(cat, e, n, sid) for n, e in enumerate(entries, 1)]
    sdir = ctx.sessions / sid
    for sub in ("transcripts", "scorecards", "work", "packets"):
        (sdir / sub).mkdir(parents=True, exist_ok=True)
    save_session(ctx, sdir, session)
    rows = [f"  {i['instance_id']}  [{i['phase']}]  {budget_minutes(cat, i['stage'], i['variant'])}m  "
            f"weight={weight_for(cat, role, i['stage'], i['variant'])}" for i in session["instances"]]
    text = (f"session: {sid}\nrole={role} level={args.level} lang={args.lang} domain={session['domain']} "
            f"feedback={args.feedback} time_scale={session['time_scale']} python={session['python']}\n"
            f"cut between VO1 and VO2: {'on' if plan['cut_active'] else 'off'}\ninstances:\n"
            + "\n".join(rows) + "\n" + "\n".join("warning: " + w for w in warnings))
    emit(args, {"session": sid, "path": str(sdir), "warnings": warnings, "config": {k: v for k, v in session.items() if k != "instances"},
                "instances": session["instances"], "cut": plan["cut"]}, text)
    return 0


def validate_new_args(cat: dict, args) -> list[str]:
    errs = []
    if args.role not in cat["roles"]:
        errs.append(f"invalid role '{args.role}'. Valid: {', '.join(cat['roles'])}")
    if args.level not in LEVELS:
        errs.append(f"invalid level '{args.level}'. Valid: {', '.join(LEVELS)}")
    if args.lang not in LANGS:
        errs.append(f"invalid lang '{args.lang}'. Valid: {', '.join(LANGS)}")
    if args.domain and args.domain not in cat["domains"]:
        errs.append(f"invalid domain '{args.domain}'. Valid: {', '.join(cat['domains'])}")
    if args.feedback not in FEEDBACK:
        errs.append(f"invalid feedback '{args.feedback}'. Valid: {', '.join(FEEDBACK)}")
    if float(args.time_scale) <= 0:
        errs.append("time_scale must be > 0")
    if args.background and not Path(args.background).is_file():
        errs.append(f"background file not found: {args.background}")
    return errs


def new_instance(cat: dict, entry: dict, n: int, sid: str) -> dict:
    iid = f"{n:02d}-{entry['stage']}@{entry['variant']}"
    return {"instance_id": iid, "stage": entry["stage"], "variant": entry["variant"], "phase": entry["phase"],
            "status": "pending", "segments": [], "agent_name": agent_name(iid, sid, 1), "attempt": 1,
            "question_ids": []}


# ------------------------------------------------------------------ clock
def touch(inst: dict, now: datetime, cap: timedelta, open_if_closed: bool = True) -> None:
    """Record activity: extend the open segment (or split it after a long idle gap)."""
    segs = inst.setdefault("segments", [])
    open_seg = segs[-1] if segs and not segs[-1].get("end") else None
    if open_seg:
        last = parse_iso(open_seg.get("last") or open_seg["start"])
        if now - last > cap:
            open_seg["end"] = iso(last + cap)
            open_seg = None
        else:
            open_seg["last"] = iso(now)
    if open_seg is None and open_if_closed:
        segs.append({"start": iso(now), "end": None, "last": iso(now)})
    if inst.get("status") == "pending":
        inst["status"] = "in_progress"


def close_segment(inst: dict, now: datetime, cap: timedelta) -> None:
    segs = inst.get("segments") or []
    if segs and not segs[-1].get("end"):
        last = parse_iso(segs[-1].get("last") or segs[-1]["start"])
        segs[-1]["end"] = iso(min(now, last + cap))


def active_seconds(inst: dict, now: datetime, cap: timedelta) -> float:
    total = 0.0
    for seg in inst.get("segments") or []:
        start = parse_iso(seg["start"])
        if seg.get("end"):
            end = parse_iso(seg["end"])
        else:
            end = min(now, parse_iso(seg.get("last") or seg["start"]) + cap)
        total += max(0.0, (end - start).total_seconds())
    return total


def clock(ctx: Ctx, cat: dict, session: dict, inst: dict) -> dict:
    scale = float(session.get("time_scale") or 1.0)
    active = active_seconds(inst, ctx.now(), ctx.idle_cap) / 60.0
    t = active / scale
    budget = budget_minutes(cat, inst["stage"], inst["variant"])
    return {"active_min": round(active, 2), "t_min": int(t), "budget_min": budget,
            "pct": round(t / budget * 100, 1), "time_scale": scale}


def flags_sent(turns: list[dict]) -> int:
    sent = 0
    for t in turns:
        if t["role"] == "orchestrator":
            for pct, text in FLAGS:
                if text in t["body"]:
                    sent = max(sent, pct)
    return sent


def new_flag(pct: float, sent: int):
    for level, text in FLAGS:
        if pct >= level and level > sent:
            return level, text
    return None


# ------------------------------------------------------------- transcript
_FORGE = re.compile(r"^(\s*)###(\s+T\d+\s+·)", re.M)
_INJECT = re.compile(r"</?\s*orchestrator[^>]*>|\[\s*orchestrator\s*:|</?\s*candidate\s*>", re.I)


def sanitize(text: str) -> str:
    """Strip orchestrator/candidate markers and neutralize forged transcript headers."""
    text = _INJECT.sub("", text)
    return _FORGE.sub(r"\1\\###\2", text).strip()


def transcript_path(sdir: Path, inst: dict) -> Path:
    return sdir / "transcripts" / f"{inst['instance_id']}.md"


def ensure_transcript(ctx, cat, sdir, session, inst) -> Path:
    path = transcript_path(sdir, inst)
    if not path.exists():
        front = {"instance_id": inst["instance_id"], "session_id": session["id"], "stage": inst["stage"],
                 "variant": inst["variant"], "phase": inst["phase"], "role": session["role"],
                 "level": session["level"], "lang": session["lang"], "domain": session["domain"],
                 "time_scale": session["time_scale"], "budget_minutes": budget_minutes(cat, inst["stage"], inst["variant"])}
        atomic_write(path, yamlish.join_front_matter(front, ""))
    return path


def read_turns(path: Path) -> list[dict]:
    return content.parse_transcript(read_text(path))[1] if path.exists() else []


def append_turn(path: Path, role: str, t_min: int, body: str) -> int:
    n = max([t["n"] for t in read_turns(path)] or [0]) + 1
    old = read_text(path)
    atomic_write(path, old.rstrip("\n") + f"\n\n### T{n} · {role} · t={t_min:02d}m\n\n{body.strip()}\n")
    return n


def cmd_turn(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    if inst["status"] in ("done", "skipped"):
        raise SimError(f"instance {inst['instance_id']} is {inst['status']}")
    ensure_writable(ctx)
    text = sanitize(input_text(args))
    touch(inst, ctx.now(), ctx.idle_cap)
    path = ensure_transcript(ctx, cat, sdir, session, inst)
    prior = read_turns(path)
    clk = clock(ctx, cat, session, inst)
    n = append_turn(path, "candidate", clk["t_min"], text)
    lines = [f"[t={clk['t_min']}m/{clk['budget_min']}m]"]
    flag = new_flag(clk["pct"], flags_sent(prior))
    if flag:
        lines.append(flag[1])
    lines += list(args.note or [])
    if len(lines) > 1:
        append_turn(path, "orchestrator", clk["t_min"], "\n".join(lines[1:]))
    save_session(ctx, sdir, session)
    message = "<orchestrator>\n" + "\n".join(lines) + "\n</orchestrator>\n<candidate>\n" + text + "\n</candidate>"
    emit(args, {"turn": n, "clock": clk, "flags": [flag[1]] if flag else [], "message": message}, message)
    return 0


_SAY = re.compile(r"<say>(.*?)</say>", re.S)
_META = re.compile(r"<meta>(.*?)</meta>", re.S)


def parse_reply(text: str) -> dict:
    """Split an interviewer reply into say/meta and list contract problems."""
    if "<say>" not in text and "&lt;say&gt;" in text:
        # Task notifications deliver the agent's final message HTML-escaped.
        text = html.unescape(text)
    problems = []
    says, metas = _SAY.findall(text), _META.findall(text)
    if len(says) != 1:
        problems.append(f"expected exactly one <say> block, found {len(says)}")
    if len(metas) != 1:
        problems.append(f"expected exactly one <meta> block, found {len(metas)}")
    out = {"say": says[0].strip() if says else "", "meta": metas[0].strip("\n") if metas else "",
           "problems": problems, "warnings": [], "meta_data": {}}
    if not problems:
        if text.rfind("</meta>") < text.rfind("</say>"):
            problems.append("<meta> must come after <say>")
        if text[text.rfind("</meta>") + len("</meta>"):].strip():
            problems.append("text found after </meta>")
        if not out["say"]:
            problems.append("<say> is empty")
    if metas:
        try:
            data = yamlish.loads(out["meta"])
            out["meta_data"] = data if isinstance(data, dict) else {}
        except yamlish.YamlError as exc:
            out["warnings"].append(f"<meta> is not valid YAML-subset ({exc}); stored raw")
            for key in ("phase", "question_id"):
                m = re.search(rf"^{key}:\s*(\S+)", out["meta"], re.M)
                if m:
                    out["meta_data"][key] = m.group(1)
    return out


def cmd_log(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    ensure_writable(ctx)
    raw = input_text(args)
    result = {"role": args.role, "ok": True, "warnings": []}
    if args.role == "interviewer":
        parsed = parse_reply(raw)
        result["warnings"] = parsed["warnings"]
        if parsed["problems"] and not args.accept_malformed:
            result.update(ok=False, problems=parsed["problems"])
            emit(args, result, "malformed reply: " + "; ".join(parsed["problems"]) + "\nAsk the interviewer to reformat once.")
            return 3
        if parsed["problems"]:
            body = raw.strip() + "\n\n<meta>\nmalformed: true\n</meta>"
            result.update(say=raw.strip(), malformed=True, closed=False)
        else:
            body = parsed["say"] + "\n\n<meta>\n" + parsed["meta"] + "\n</meta>"
            result.update(say=parsed["say"], malformed=False,
                          closed=parsed["meta_data"].get("phase") == "closed")
    else:
        body = sanitize(raw) if args.role != "ai-pair" else raw.strip()
    path = ensure_transcript(ctx, cat, sdir, session, inst)
    touch(inst, ctx.now(), ctx.idle_cap, open_if_closed=not inst.get("segments"))
    clk = clock(ctx, cat, session, inst)
    if args.role == "interviewer" and not result.get("malformed"):
        if store_profile(session, parsed["meta_data"], parsed["meta"]):
            result["candidate_profile_stored"] = True
    result["turn"] = append_turn(path, args.role, clk["t_min"], body)
    result["clock"] = clk
    save_session(ctx, sdir, session)
    emit(args, result, f"logged T{result['turn']} ({args.role})" + (" [stage closed]" if result.get("closed") else ""))
    return 0


def store_profile(session: dict, meta: dict, raw_meta: str) -> bool:
    """Keep hm-screen's `candidate_profile_summary` as session `candidate_profile` (later launch packets use it)."""
    summary = meta.get("candidate_profile_summary")
    if summary is None and "candidate_profile_summary" in raw_meta:
        m = re.search(r"^candidate_profile_summary:[ \t]*(.*(?:\n[ \t]+.*)*)", raw_meta, re.M)
        summary = m.group(1) if m else None
    if summary in (None, "", [], {}):
        return False
    text = summary.strip() if isinstance(summary, str) else yamlish.dumps(summary).strip()
    if not text:
        return False
    old = str(session.get("candidate_profile") or "").strip()
    if old and old != text:
        if text in old:
            return False
        text = old + "\n\nAdded from the HM screen:\n" + text
    session["candidate_profile"] = text
    return True


def cmd_pause(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    ensure_writable(ctx)
    close_segment(inst, ctx.now(), ctx.idle_cap)
    save_session(ctx, sdir, session)
    clk = clock(ctx, cat, session, inst)
    resume = f"resume with: sim.py state {session['id']}  (the next `turn` reopens the clock)"
    emit(args, {"paused": True, "clock": clk, "resume_hint": resume},
         f"paused {inst['instance_id']} at t={clk['t_min']}m/{clk['budget_min']}m; {resume}")
    return 0


def cmd_end(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    ensure_writable(ctx)
    close_segment(inst, ctx.now(), ctx.idle_cap)
    inst["end_reason"] = args.reason
    inst["status"] = "skipped" if args.reason == "skipped" else "done"
    save_session(ctx, sdir, session)
    cause = END_REASONS[args.reason]
    hint = ("uncovered competencies become no_evidence" if cause == "external"
            else "score every competency and list the uncovered signal points")
    emit(args, {"instance": inst["instance_id"], "status": inst["status"], "end_reason": args.reason,
                "cause": cause, "evaluation_hint": hint, "clock": clock(ctx, cat, session, inst)},
         f"{inst['instance_id']} -> {inst['status']} ({args.reason}, {cause} cause): {hint}")
    return 0


def cmd_set(ctx: Ctx, args) -> int:
    sdir, session = resolve_session(ctx, args.session)
    target = get_instance(session, args.instance) if args.instance else session
    allowed = INSTANCE_KEYS if args.instance else SESSION_KEYS
    for pair in args.pairs:
        key, sep, raw = pair.partition("=")
        if not sep or key not in allowed:
            raise SimError(f"cannot set '{key}'. Allowed: {', '.join(allowed)} (use key=value)")
        value = read_text(raw[1:]).strip() if raw.startswith("@") else yamlish.parse_inline(raw)
        validate_set(key, value)
        target[key] = value
    save_session(ctx, sdir, session)
    emit(args, {"updated": args.pairs}, "updated: " + ", ".join(args.pairs))
    return 0


def validate_set(key: str, value) -> None:
    enums = {"status": STATUSES, "mode": MODES, "feedback": FEEDBACK, "end_reason": tuple(END_REASONS),
             "level": LEVELS, "lang": tuple(LANGS)}
    if key in enums and value not in enums[key]:
        raise SimError(f"invalid {key} '{value}'. Valid: {', '.join(enums[key])}")
    if key == "cut" and not (isinstance(value, dict) and value.get("outcome") in ("continue", "stop")):
        raise SimError("cut must be {outcome: continue|stop, reason: ...}")
    if key == "final" and not (isinstance(value, dict) and value.get("outcome") in ("hire", "no_hire", "referred")):
        raise SimError("final must be {outcome: hire|no_hire|referred, level: L5, override: false}")


# ----------------------------------------------------------------- select
def item_meta(path: Path) -> dict:
    if path.is_dir():
        for name in ("problem.md", "context.md", "prompt.md", "tasks.md", "notes.md"):
            if (path / name).is_file():
                try:
                    return yamlish.split_front_matter(read_text(path / name))[0]
                except yamlish.YamlError:
                    return {}
    return {}


def material_dirs(ctx: Ctx, stage: dict, variant: str) -> list[str]:
    vd = variant_def(stage, variant)
    if vd and vd.get("materials"):
        return list(vd["materials"])
    if not stage.get("variants"):
        return [d for d in MATERIAL_DIRS if (ctx.stages / stage["id"] / d).is_dir()]
    return []


def list_items(ctx: Ctx, stage_id: str, dirname: str) -> list[Path]:
    root = ctx.stages / stage_id / dirname
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if (p.is_dir() and not p.name.startswith(".")) or p.suffix == ".sql")


def item_id(path: Path) -> str:
    return path.stem if path.is_file() else path.name


def used_ids(ctx: Ctx, skip_instance: str | None = None, skip_session: str | None = None) -> set[tuple[str, str]]:
    used = set()
    for sdir, sess in list_sessions(ctx):
        for inst in sess.get("instances") or []:
            if sdir.name == skip_session and inst["instance_id"] == skip_instance:
                continue
            for qid in inst.get("question_ids") or []:
                used.add((inst["stage"], str(qid)))
            if inst.get("problem_id"):
                used.add((inst["stage"], str(inst["problem_id"])))
    return used


def pick(items: list, is_used, rng: random.Random, n: int):
    fresh = [i for i in items if not is_used(i)]
    stale = [i for i in items if is_used(i)]
    rng.shuffle(fresh)
    rng.shuffle(stale)
    chosen = (fresh + stale)[:n]
    return chosen, [c for c in chosen if is_used(c)]


def locate_material(ctx: Ctx, stage_id: str, pid: str):
    for d in MATERIAL_DIRS:
        for p in list_items(ctx, stage_id, d):
            if item_id(p) == pid:
                return d, p
    return None, None


def select_content(ctx, cat, sdir, session, inst, args) -> dict:
    """Pick questions and one material item for an instance (idempotent unless reselect)."""
    stage = stage_def(cat, inst["stage"])
    sdir_stage = ctx.stages / inst["stage"]
    role, level, domain, variant = session["role"], session["level"], session["domain"], inst["variant"]
    rng = random.Random(f"{session['id']}|{inst['instance_id']}|{args.seed}")
    used = used_ids(ctx, inst["instance_id"], sdir.name)
    qpath = sdir_stage / "questions.md"
    questions = content.parse_questions(read_text(qpath)) if qpath.is_file() else []
    pool = [q for q in questions if not q["error"] and q["meta"].get("kind") == "main"
            and content.matches(q["meta"], role, level, variant, domain)]
    reused, material = [], None
    kept_q = [q for qid in (inst.get("question_ids") or []) for q in pool if q["id"] == qid] if not args.reselect else []
    kept_m = None
    if inst.get("problem_id") and not args.reselect:
        d, p = locate_material(ctx, inst["stage"], inst["problem_id"])
        kept_m = (d, p) if p else None
    items = []
    if not kept_m:
        for d in material_dirs(ctx, stage, variant):
            for p in list_items(ctx, inst["stage"], d):
                if content.matches(item_meta(p), role, level, variant, domain):
                    items.append((d, p))
        if items:
            chosen, stale = pick(items, lambda it: (inst["stage"], item_id(it[1])) in used, rng, 1)
            material = chosen[0]
            reused += [item_id(c[1]) for c in stale]
    else:
        material = kept_m
    n_q = args.count or (2 if material else max(2, round(budget_minutes(cat, inst["stage"], variant) / 20)))
    if kept_q:
        selected_q = kept_q
    else:
        selected_q, stale = pick(pool, lambda q: (inst["stage"], q["id"]) in used, rng, n_q)
        reused += [q["id"] for q in stale]
    if not selected_q and not material:
        raise SimError(f"no content for {inst['stage']}@{variant} (role={role}, level={level}, domain={domain}). "
                       f"Run: check_simulator.py --stage {inst['stage']}")
    probes = []
    if inst["stage"] != "culture":
        cpool = [q for q in questions if not q["error"] and q["meta"].get("kind") == "culture"
                 and content.matches(q["meta"], role, level, variant, domain)]
        probes, _ = pick(cpool, lambda q: False, rng, 2)
    return {"questions": selected_q, "probes": probes, "material": material, "reused": reused}


def prepare_work(ctx, sdir, inst, material) -> list[str]:
    """Copy candidate-facing materials into the session workspace."""
    if not material:
        return []
    dirname, path = material
    work = sdir / "work" / inst["instance_id"]
    work.mkdir(parents=True, exist_ok=True)
    notes = []
    if dirname == "problems" and (path / "starter.py").is_file():
        if not (work / "solution.py").exists():
            shutil.copyfile(path / "starter.py", work / "solution.py")
        notes.append("solution.py")
    elif dirname == "repos" and (path / "workspace").is_dir():
        _testrun.copy_tree(path / "workspace", work)
        notes.append("workspace/ contents")
    elif dirname == "takehomes":
        shutil.copyfile(path / "prompt.md", work / "prompt.md")
        run_generator(path, work)
        notes.append("prompt.md + generated data")
    elif dirname == "datasets":
        shutil.copyfile(path, work / "dataset.sql")
        build_sqlite(path, work / "data.sqlite3")
        notes.append("dataset.sql + data.sqlite3")
    return notes


def run_generator(takehome: Path, work: Path) -> None:
    gen = takehome / "generate_data.py"
    if not gen.is_file():
        return
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, str(gen), str(work)], cwd=str(work), capture_output=True,
                          text=True, env=env, timeout=300)
    if proc.returncode != 0:
        raise SimError("generate_data.py failed (are numpy/pandas installed? pip install -r "
                       f"netflix-ml-interview/requirements.txt): {proc.stderr.strip()[-300:]}")


def build_sqlite(sql_file: Path, db_file: Path) -> None:
    if db_file.exists():
        db_file.unlink()
    con = sqlite3.connect(str(db_file))
    try:
        con.executescript(read_text(sql_file))
        con.commit()
    finally:
        con.close()


def read_if(path: Path) -> str:
    return read_text(path).strip() if path.is_file() else ""


def render_material(ctx, inst, material) -> str:
    if not material:
        return "(no separate material for this instance)"
    dirname, path = material
    if dirname == "problems":
        parts = [("Problem", "problem.md"), ("Follow-ups", "followups.md")]
        extra = "Interviewer-only files you may Read on your first turn: reference.py, tests.py in the same folder."
    elif dirname == "repos":
        parts, extra = [("Tasks given to the candidate", "tasks.md"), ("Interviewer notes", "notes.md")], ""
    elif dirname == "prs":
        parts = [("PR diff", "pr.diff"), ("Context", "context.md"), ("Known issues (interviewer only)", "issues.md")]
        extra = ""
    elif dirname == "takehomes":
        parts, extra = [("Take-home prompt", "prompt.md")], "Candidate data was generated in the session workspace."
    else:
        head = "\n".join(read_text(path).splitlines()[:60])
        return f"### Dataset `{item_id(path)}` (first lines)\n\n```sql\n{head}\n```"
    blocks = [f"### {title}\n\n{read_if(path / fname) or '(missing)'}" for title, fname in parts]
    out = f"Material id: `{item_id(path)}`\n\n" + "\n\n".join(blocks)
    return out + (f"\n\n{extra}\nFolder: {path}" if extra else "")


def render_question(q: dict) -> str:
    sp = q["meta"].get("signal_points") or []
    sp_text = "\n".join(f"- {s}" for s in sp)
    return f"### {q['id']}\n\nSignal points:\n{sp_text}\n\n{q['body']}"


def build_packet(ctx, cat, sdir, session, inst, chosen) -> str:
    stage = stage_def(cat, inst["stage"])
    persona = stage["persona"]
    brief = read_if(ctx.stages / inst["stage"] / "brief.md") or "(brief.md missing)"
    profile = session.get("candidate_profile") or "(none provided: if this stage needs it, ask the candidate to summarize their background)"
    lang_name = LANGS[session["lang"]]
    qs = "\n\n".join(render_question(q) for q in chosen["questions"]) or "(none)"
    probes = "\n\n".join(render_question(q) for q in chosen["probes"])
    clk_budget = budget_minutes(cat, inst["stage"], inst["variant"])
    work = sdir / "work" / inst["instance_id"]
    workspace_line = (f"- candidate workspace (their files live here; tell them the path): {work.resolve()}\n"
                      if chosen["material"] and work.is_dir() else "")
    return f"""# Launch packet: {inst['instance_id']}

## Config
- instance: {inst['instance_id']} (stage `{inst['stage']}`, variant `{inst['variant']}`, phase `{inst['phase']}`)
- candidate role: {session['role']} ({cat['roles'][session['role']]['label']}); target level: {session['level']}; domain: {session['domain']}
- time budget: {clk_budget} minutes of candidate time scaled by time_scale={session['time_scale']} (the orchestrator sends time flags; obey them)
- session language: {lang_name}
{workspace_line}
## Persona
You are {persona['name']}, {persona['title']}. Interview style: {persona['style']} (style changes tone, not rigor).

## Language rule
Conduct the entire stage in {lang_name}, even if the candidate switches language. Note a switch as `lang_switch: true` in `<meta>`; never penalize it.

## Turn contract
{TURN_CONTRACT}

## Brief
{brief}

## Selected questions
{qs}

## Culture probes (optional, use when they fit)
{probes or '(none)'}

## Material
{render_material(ctx, inst, chosen['material'])}

## Candidate profile
{profile}
"""


def cmd_select(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    ensure_writable(ctx)
    chosen = select_content(ctx, cat, sdir, session, inst, args)
    notes = prepare_work(ctx, sdir, inst, chosen["material"])
    inst["question_ids"] = [q["id"] for q in chosen["questions"]]
    if chosen["material"]:
        inst["problem_id"] = item_id(chosen["material"][1])
    packet = build_packet(ctx, cat, sdir, session, inst, chosen)
    atomic_write(sdir / "packets" / f"{inst['instance_id']}.md", packet)
    save_session(ctx, sdir, session)
    if chosen["reused"]:
        warn("no unused alternatives left for: " + ", ".join(chosen["reused"]) + " (reusing)")
    emit(args, {"instance": inst["instance_id"], "question_ids": inst["question_ids"],
                "problem_id": inst.get("problem_id"), "workspace": notes, "reused": chosen["reused"],
                "packet_path": str(sdir / "packets" / f"{inst['instance_id']}.md"), "packet": packet}, packet)
    return 0


def cmd_rebuild(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    ensure_writable(ctx)
    if inst["status"] in ("done", "skipped"):
        raise SimError(f"instance {inst['instance_id']} is {inst['status']}; nothing to rebuild")
    close_segment(inst, ctx.now(), ctx.idle_cap)
    inst["attempt"] = int(inst.get("attempt") or 1) + 1
    inst["agent_name"] = agent_name(inst["instance_id"], session["id"], inst["attempt"])
    inst["status"] = "in_progress"
    chosen = select_content(ctx, cat, sdir, session, inst, argparse.Namespace(seed=0, count=None, reselect=False))
    packet = build_packet(ctx, cat, sdir, session, inst, chosen)
    clk = clock(ctx, cat, session, inst)
    tpath = transcript_path(sdir, inst)
    history = read_text(tpath).split("---\n", 2)[-1].strip() if tpath.exists() else "(empty)"
    remaining = max(0, clk["budget_min"] - clk["t_min"])
    prompt = (f"{packet}\n## Transcript so far (includes your own <meta> blocks)\n\n{history}\n\n"
              f"## Time\nElapsed t={clk['t_min']}m of {clk['budget_min']}m; remaining about {remaining}m.\n\n"
              "## Instruction\nContinue as the same persona; do not re-introduce yourself; respond to the last "
              "candidate message.\n")
    save_session(ctx, sdir, session)
    emit(args, {"agent_name": inst["agent_name"], "attempt": inst["attempt"], "clock": clk, "prompt": prompt}, prompt)
    return 0


# ------------------------------------------------------- tests and patches
def cmd_run_tests(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    work = sdir / "work" / inst["instance_id"]
    pid = inst.get("problem_id")
    dirname, path = locate_material(ctx, inst["stage"], pid) if pid else (None, None)
    if not path:
        raise SimError("this instance has no problem/repo selected (run `select` first)")
    results = {}
    if dirname == "repos":
        results["tests"] = _testrun.run_in_scratch({}, base=work, timeout=args.timeout)
    else:
        tests = path / "tests.py"
        if not tests.is_file():
            raise SimError(f"{tests} not found")
        results["tests"] = _testrun.run_in_scratch({"tests.py": tests}, base=work, timeout=args.timeout,
                                                   mode="module", target="tests")
        own = [p for p in work.glob("test*.py")] if work.is_dir() else []
        if own:
            results["candidate-tests"] = _testrun.run_in_scratch({}, base=work, timeout=args.timeout)
    lines = [_testrun.format_result(r, label) for label, r in results.items()]
    if args.hidden:
        lines += hidden_results(path, work, args.timeout)
    message = " ".join(lines)
    if not args.no_log:
        ensure_writable(ctx)
        tpath = ensure_transcript(ctx, cat, sdir, session, inst)
        touch(inst, ctx.now(), ctx.idle_cap, open_if_closed=False)
        append_turn(tpath, "orchestrator", clock(ctx, cat, session, inst)["t_min"], message)
        save_session(ctx, sdir, session)
    emit(args, {"results": results, "message": message}, message)
    ok = all(not r["error"] and not r["failing"] and r["total"] > 0 for r in results.values())
    return 0 if ok else 1


def hidden_results(repo: Path, work: Path, timeout: int) -> list[str]:
    flaws_file = repo / "flaws.yaml"
    flaws = (yamlish.loads(read_text(flaws_file)) or {}).get("flaws") or [] if flaws_file.is_file() else []
    lines = []
    for fl in flaws:
        src = repo / str(fl.get("hidden_test", ""))
        if not src.is_file():
            lines.append(f"[hidden: {fl.get('id')} test missing]")
            continue
        mod = "hidden_" + re.sub(r"\W", "_", str(fl["id"]))
        res = _testrun.run_in_scratch({mod + ".py": src}, base=work, timeout=timeout, mode="module", target=mod)
        verdict = "flaw present" if (res["failing"] or res["error"]) else "clean"
        lines.append(f"[hidden: {fl['id']} {verdict}]")
    return lines or ["[hidden: no flaws defined]"]


def cmd_apply(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    ensure_writable(ctx)
    work = sdir / "work" / inst["instance_id"]
    work.mkdir(parents=True, exist_ok=True)
    try:
        changes = _patch.apply_patch(work, input_text(args), dry_run=args.check)
    except _patch.PatchError as exc:
        raise SimError(f"patch rejected, nothing changed: {exc}", 1)
    summary = ", ".join(f"{c['path']} (+{c['added']}/-{c['removed']})" for c in changes)
    if not args.check and not args.no_log:
        touch(inst, ctx.now(), ctx.idle_cap, open_if_closed=False)
        append_turn(ensure_transcript(ctx, cat, sdir, session, inst), "orchestrator",
                    clock(ctx, cat, session, inst)["t_min"], f"[applied diff: {summary}]")
        save_session(ctx, sdir, session)
    emit(args, {"applied": not args.check, "changes": changes}, ("would apply: " if args.check else "applied: ") + summary)
    return 0


# ------------------------------------------------------------- evaluation
def cmd_transcript(ctx: Ctx, args) -> int:
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    text = read_text(transcript_path(sdir, inst))
    if args.for_evaluator:
        text = content.strip_notes_private(text)
    if args.out:
        ensure_writable(ctx)
        atomic_write(Path(args.out), text)
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def cmd_recommend(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    front, _ = yamlish.split_front_matter(read_text(args.scorecard))
    core = core_ids(cat, front.get("stage"))
    rec = content.derive_recommendation(front.get("scores") or {}, core)
    emit(args, {"recommendation": rec, "core": sorted(core)}, rec)
    return 0


def core_ids(cat: dict, stage: str | None) -> set[str]:
    try:
        return {c["id"] for c in stage_def(cat, stage)["competencies"] if c["core"]}
    except SimError:
        return set()


def verify_scorecard(cat: dict, front: dict, turns: list[dict]) -> dict:
    """Check evidence quotes, hint caps, score enums and the derived recommendation."""
    by_n = {t["n"]: t for t in turns}
    scores, evidence = front.get("scores") or {}, front.get("evidence") or {}
    errors = []
    for comp, score in scores.items():
        if score not in content.SCORES:
            errors.append({"competency": comp, "kind": "bad_score", "detail": str(score)})
            continue
        entries = evidence.get(comp) or []
        if not isinstance(entries, list):
            entries = [entries]
        if score != "no_evidence" and not entries:
            errors.append({"competency": comp, "kind": "missing_evidence", "detail": "no evidence entries"})
        for e in entries:
            errors += check_quote(comp, e, by_n)
    errors += hint_errors(front, scores)
    stage = front.get("stage")
    warnings = []
    try:
        wanted = {c["id"] for c in stage_def(cat, stage)["competencies"]}
        for missing in sorted(wanted - set(scores)):
            errors.append({"competency": missing, "kind": "missing_score", "detail": "competency not scored"})
        for extra in sorted(set(scores) - wanted):
            errors.append({"competency": extra, "kind": "unknown_competency", "detail": stage})
        expected = content.derive_recommendation(scores, core_ids(cat, stage))
        if front.get("recommendation") != expected:
            errors.append({"competency": "-", "kind": "recommendation_mismatch",
                           "detail": f"scorecard says {front.get('recommendation')}, rule gives {expected}"})
    except SimError:
        warnings.append(f"stage '{stage}' not in catalog: competency/recommendation checks skipped")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def check_quote(comp: str, entry, by_n: dict) -> list[dict]:
    if not isinstance(entry, dict):
        return [{"competency": comp, "kind": "bad_turn_id", "turn_id": None, "detail": "evidence entry must be {turn_id, quote}"}]
    raw_id = entry.get("turn_id")
    try:
        tid = int(str(raw_id).lstrip("Tt"))
    except (TypeError, ValueError):
        return [{"competency": comp, "kind": "bad_turn_id", "turn_id": raw_id, "detail": "turn_id must be a number"}]
    turn = by_n.get(tid)
    if turn is None:
        return [{"competency": comp, "kind": "turn_not_found", "turn_id": tid, "detail": f"no T{tid}"}]
    if turn["role"] != "candidate":
        return [{"competency": comp, "kind": "not_candidate_turn", "turn_id": tid, "detail": f"T{tid} is {turn['role']}"}]
    quote = content.norm_text(entry.get("quote", ""))
    if not quote or quote not in content.norm_text(turn["body"]):
        return [{"competency": comp, "kind": "quote_not_found", "turn_id": tid, "detail": str(entry.get("quote", ""))[:80]}]
    return []


def hint_errors(front: dict, scores: dict) -> list[dict]:
    caps = {"nudge": "Y", "substantive": "N"}
    errs = []
    for h in front.get("hints") or []:
        cap = caps.get(h.get("level"))
        comp = h.get("competency")
        score = scores.get(comp)
        if cap and score in content.SCORE_RANK and content.SCORE_RANK[score] > content.SCORE_RANK[cap]:
            errs.append({"competency": comp, "kind": "hint_cap_violated",
                         "detail": f"{h.get('level')} hint caps at {cap}, scored {score}"})
    return errs


def downgrade(cat: dict, front: dict, report: dict) -> list[str]:
    """Set competencies with evidence errors to no_evidence and recompute the recommendation."""
    bad = {e["competency"] for e in report["errors"]
           if e["kind"] in ("turn_not_found", "not_candidate_turn", "quote_not_found", "bad_turn_id", "missing_evidence")}
    notes = []
    for comp in sorted(bad):
        if comp in (front.get("scores") or {}):
            front["scores"][comp] = "no_evidence"
            (front.setdefault("evidence", {}))[comp] = []
            notes.append(f"{comp}: downgraded to no_evidence (evidence not verifiable)")
    front["recommendation"] = content.derive_recommendation(front.get("scores") or {}, core_ids(cat, front.get("stage")))
    front["warnings"] = list(front.get("warnings") or []) + notes
    return notes


def cmd_verify(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    if args.scorecard and args.transcript:
        sc_path, tr_path = Path(args.scorecard), Path(args.transcript)
    elif args.session and args.instance:
        sdir, session = resolve_session(ctx, args.session)
        inst = get_instance(session, args.instance)
        sc_path = Path(args.scorecard) if args.scorecard else sdir / "scorecards" / f"{inst['instance_id']}.md"
        tr_path = Path(args.transcript) if args.transcript else transcript_path(sdir, inst)
    else:
        raise SimError("use --scorecard and --transcript, or --session and --instance")
    front, body = yamlish.split_front_matter(read_text(sc_path))
    turns = content.parse_transcript(read_text(tr_path))[1]
    report = verify_scorecard(cat, front, turns)
    if args.downgrade and not report["ok"]:
        ensure_writable(ctx)
        report["downgraded"] = downgrade(cat, front, report)
        atomic_write(sc_path, yamlish.join_front_matter(front, body))
    lines = [("OK: all evidence verified" if report["ok"] else "FAILED:")]
    lines += [f"  {e['competency']}: {e['kind']} {('T' + str(e['turn_id'])) if 'turn_id' in e else ''} {e['detail']}" for e in report["errors"]]
    lines += [f"  downgrade: {n}" for n in report.get("downgraded", [])] + [f"warning: {w}" for w in report["warnings"]]
    emit(args, report, "\n".join(lines))
    return 0 if report["ok"] else 1


# ------------------------------------------------------- writing results
SCORECARD_LEVELS = ("L4", "L5", "L6", "none")
RECOMMENDATIONS = ("pass", "fail", "insufficient_signal")
OUTCOMES = {"cut": ("continue", "stop"), "final": ("hire", "no_hire", "referred")}
CULTURE_VERDICTS = ("positive", "negative", "mixed")


def unfence(text: str) -> str:
    """Drop a ```markdown fence an agent may have wrapped around its document."""
    t = text.strip("\n")
    lines = t.split("\n")
    if lines and lines[0].lstrip().startswith("```") and len(lines) > 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]) + "\n"
    return t + "\n"


def rubric_version(ctx: Ctx, stage: str):
    path = ctx.stages / stage / "rubric.md"
    if not path.is_file():
        return None
    try:
        return yamlish.split_front_matter(read_text(path))[0].get("rubric_version")
    except yamlish.YamlError:
        return None


def front_errors(cat: dict, ctx: Ctx, session: dict, inst: dict, front: dict) -> list[dict]:
    """Validate a scorecard front-matter against templates/scorecard.md and the D10 enums."""
    errs = []

    def bad(detail, kind="front_matter"):
        errs.append({"competency": "-", "kind": kind, "detail": detail})

    for key in ("instance_id", "stage", "variant", "level", "rubric_version", "recommendation",
                "level_observed", "scores", "evidence", "hints"):
        if key not in front:
            bad(f"missing key '{key}'")
    for key in ("instance_id", "stage", "variant"):
        if key in front and front[key] != inst[key]:
            bad(f"{key} is '{front[key]}', the instance has '{inst[key]}'")
    if "level" in front and front["level"] != session["level"]:
        bad(f"level is '{front['level']}', the session target is '{session['level']}'")
    if "recommendation" in front and front["recommendation"] not in RECOMMENDATIONS:
        bad(f"recommendation '{front['recommendation']}' must be one of {', '.join(RECOMMENDATIONS)}")
    if "level_observed" in front and front["level_observed"] not in SCORECARD_LEVELS:
        bad(f"level_observed '{front['level_observed']}' must be one of {', '.join(SCORECARD_LEVELS)}")
    want = rubric_version(ctx, inst["stage"])
    if "rubric_version" in front:
        if not isinstance(front["rubric_version"], int) or isinstance(front["rubric_version"], bool):
            bad("rubric_version must be an integer")
        elif want is not None and front["rubric_version"] != want:
            bad(f"rubric_version is {front['rubric_version']}, the rubric has {want}")
    for key in ("scores", "evidence"):
        if key in front and not isinstance(front[key], dict):
            bad(f"'{key}' must be a map")
    if "hints" in front:
        if not isinstance(front["hints"], list):
            bad("'hints' must be a list")
        else:
            for h in front["hints"]:
                if not (isinstance(h, dict) and h.get("level") in ("nudge", "substantive") and h.get("competency")):
                    bad(f"hint {h!r} must be {{id, level: nudge|substantive, competency}}")
    if isinstance(front.get("scores"), dict):
        for comp, score in front["scores"].items():
            if score not in content.SCORES:
                errs.append({"competency": comp, "kind": "bad_score", "detail": str(score)})
    return errs


def _report(front_errs: list[dict], front: dict, turns: list[dict], cat: dict) -> dict:
    """Front-matter problems first; the quote/rule checks only run on a well-formed map."""
    if any(e["kind"] == "front_matter" for e in front_errs) and not isinstance(front.get("scores"), dict):
        return {"ok": False, "errors": front_errs, "warnings": []}
    rep = verify_scorecard(cat, front, turns)
    seen = {(e["competency"], e["kind"]) for e in front_errs}
    rep["errors"] = front_errs + [e for e in rep["errors"] if (e["competency"], e["kind"]) not in seen]
    rep["ok"] = not rep["errors"]
    return rep


def format_report(report: dict, ok_text: str) -> str:
    lines = [ok_text if report["ok"] else "FAILED:"]
    lines += [f"  {e['competency']}: {e['kind']} {('T' + str(e['turn_id'])) if 'turn_id' in e else ''} {e['detail']}"
              for e in report["errors"]]
    lines += [f"  downgrade: {n}" for n in report.get("downgraded", [])]
    lines += [f"warning: {w}" for w in report.get("warnings", [])]
    return "\n".join(lines)


def cmd_write_scorecard(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    inst = get_instance(session, args.instance)
    ensure_writable(ctx)
    text = unfence(input_text(args))
    try:
        front, body = yamlish.split_front_matter(text)
    except yamlish.YamlError as exc:
        raise SimError(f"scorecard front-matter is not valid YAML-subset: {exc}", 1)
    if not front:
        raise SimError("scorecard must start with a '---' front-matter block (see templates/scorecard.md)", 1)
    turns = read_turns(transcript_path(sdir, inst))
    report = _report(front_errs=front_errors(cat, ctx, session, inst, front), front=front, turns=turns, cat=cat)
    target = sdir / "scorecards" / f"{inst['instance_id']}.md"
    if not report["ok"] and args.downgrade:
        report["downgraded"] = downgrade(cat, front, report)
        text = yamlish.join_front_matter(front, body)
        after = _report(front_errors(cat, ctx, session, inst, front), front, turns, cat)
        report["errors_after_downgrade"] = after["errors"]
        report["ok"] = after["ok"]
        report["errors"] = after["errors"]
    keep = report["ok"] or args.keep_invalid
    if keep:
        atomic_write(target, text)
        inst["scorecard"] = f"scorecards/{inst['instance_id']}.md"
        save_session(ctx, sdir, session)
    if inst["status"] not in ("done", "skipped"):
        report.setdefault("warnings", []).append(f"instance is {inst['status']}; run `end` before evaluating")
    report.update(path=str(target), written=keep)
    summary = ("OK after downgrade: scorecard written; unverifiable competencies were set to no_evidence"
               if report["ok"] and report.get("downgraded") else
               "OK: scorecard written and every evidence quote verified" if report["ok"] else "FAILED:")
    msg = format_report(report, summary)
    if not report["ok"]:
        msg += ("\n  written (invalid) to " + str(target) if keep else
                "\n  nothing was written; fix the items above and send the scorecard again "
                "(--downgrade writes it with unverifiable competencies set to no_evidence)")
    emit(args, report, msg)
    return 0 if report["ok"] else 1


def debrief_errors(cat: dict, session: dict, front: dict, mode: str) -> list[str]:
    errs = []
    for key in ("type", "session_id", "role", "target_level", "complete", "provisional_outcome", "outcome", "level",
                "override", "culture_verdict", "stages_considered"):
        if key not in front:
            errs.append(f"missing key '{key}'")
    if errs:
        return errs
    if front["type"] != mode:
        errs.append(f"type is '{front['type']}', expected '{mode}'")
    if front["session_id"] != session["id"]:
        errs.append(f"session_id is '{front['session_id']}', expected '{session['id']}'")
    if front["role"] != session["role"]:
        errs.append(f"role is '{front['role']}', expected '{session['role']}'")
    if front["target_level"] != session["level"]:
        errs.append(f"target_level is '{front['target_level']}', expected '{session['level']}'")
    for key in ("complete", "override"):
        if not isinstance(front[key], bool):
            errs.append(f"{key} must be true or false")
    if front["provisional_outcome"] not in OUTCOMES["final"]:
        errs.append(f"provisional_outcome must be one of {', '.join(OUTCOMES['final'])}")
    if front["outcome"] not in OUTCOMES[mode]:
        errs.append(f"outcome '{front['outcome']}' must be one of {', '.join(OUTCOMES[mode])} in {mode} mode")
    if front["level"] not in SCORECARD_LEVELS:
        errs.append(f"level must be one of {', '.join(SCORECARD_LEVELS)}")
    if front["culture_verdict"] not in CULTURE_VERDICTS:
        errs.append(f"culture_verdict must be one of {', '.join(CULTURE_VERDICTS)}")
    ids = [i["instance_id"] for i in session.get("instances") or []]
    listed = front["stages_considered"]
    if not isinstance(listed, list):
        errs.append("stages_considered must be a list")
    else:
        unknown = [x for x in listed if x not in ids]
        if unknown:
            errs.append("stages_considered has unknown instances: " + ", ".join(map(str, unknown)))
        else:
            order = catalog_order(cat, session, session.get("instances") or [])
            rank = {i["instance_id"]: n for n, i in enumerate(order)}
            if [rank[x] for x in listed] != sorted(rank[x] for x in listed):
                errs.append("stages_considered is not in catalog order: " + ", ".join(i["instance_id"] for i in order))
    if front["override"] is False and front["provisional_outcome"] in OUTCOMES["final"] and not errs:
        expect = front["provisional_outcome"] if mode == "final" else (
            "stop" if front["provisional_outcome"] == "no_hire" else "continue")
        if front["outcome"] != expect:
            errs.append(f"override is false but outcome '{front['outcome']}' differs from the provisional "
                        f"outcome (expected '{expect}'); set override: true with a justification or fix it")
    return errs


def cmd_write_debrief(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    ensure_writable(ctx)
    if args.mode == "cut" and not cat["roles"][session["role"]]["cut"]:
        raise SimError(f"role '{session['role']}' has no cut", 1)
    text = unfence(input_text(args))
    try:
        front, _ = yamlish.split_front_matter(text)
    except yamlish.YamlError as exc:
        raise SimError(f"debrief front-matter is not valid YAML-subset: {exc}", 1)
    errs = debrief_errors(cat, session, front, args.mode) if front else ["no front-matter block"]
    target = sdir / ("debrief-cut.md" if args.mode == "cut" else "debrief.md")
    if errs and not args.keep_invalid:
        emit(args, {"ok": False, "errors": errs, "written": False},
             "FAILED:\n  " + "\n  ".join(errs) + "\n  nothing was written; fix the items above and send it again")
        return 1
    atomic_write(target, text)
    if not errs:
        if args.mode == "cut":
            session["cut"] = {"outcome": front["outcome"], "reason": args.reason or f"see {target.name}"}
        else:
            session["final"] = {"outcome": front["outcome"], "level": front["level"], "override": front["override"]}
        save_session(ctx, sdir, session)
    emit(args, {"ok": not errs, "errors": errs, "written": True, "path": str(target), "outcome": front.get("outcome")},
         (f"OK: {args.mode} debrief written to {target}; session {'cut' if args.mode == 'cut' else 'final'} = "
          f"{front.get('outcome')}" if not errs else "written (invalid) to " + str(target) + ":\n  " + "\n  ".join(errs)))
    return 0 if not errs else 1


# ---------------------------------------------------------------- packets
def catalog_order(cat: dict, session: dict, instances: list[dict]) -> list[dict]:
    """Instances in the order of the role's loop (screen, vo1, vo2), then catalog stage order."""
    loop = cat["roles"][session["role"]]["loop"]
    flat = [f"{loop_entry(e)[0]}@{loop_entry(e)[1] or default_variant(stage_def(cat, loop_entry(e)[0]), session['role'])}"
            for ph in PHASES for e in loop[ph]]

    def key(item):
        n, inst = item
        tag = f"{inst['stage']}@{inst['variant']}"
        return (PHASES.index(inst["phase"]), flat.index(tag) if tag in flat else 1000,
                stage_def(cat, inst["stage"])["order"], n)
    return [i for _, i in sorted(enumerate(instances), key=key)]


def is_practice(session: dict, inst: dict) -> bool:
    cut_stop = (session.get("cut") or {}).get("outcome") == "stop"
    return session.get("mode") == "practice" and (not cut_stop or inst.get("phase") == "vo2")


def packet_file(sdir: Path, name: str, text: str) -> str:
    path = sdir / "packets" / name
    atomic_write(path, text)
    return str(path)


def scorecard_path(sdir: Path, inst: dict):
    front = load_scorecard_front(sdir, inst)
    return (sdir / "scorecards" / f"{inst['instance_id']}.md") if front else None


def evaluator_packet(ctx, cat, sdir, session, inst, args) -> str:
    st = stage_def(cat, inst["stage"])
    rub = ctx.stages / inst["stage"] / "rubric.md"
    version = rubric_version(ctx, inst["stage"])
    if version is None:
        raise SimError(f"rubric (or its rubric_version) not found: {rub}")
    tr = transcript_path(sdir, inst)
    if not tr.is_file():
        raise SimError(f"no transcript for {inst['instance_id']}")
    filtered = content.strip_notes_private(read_text(tr))
    comps = "\n".join(f"- {c['id']}: core={'true' if c['core'] else 'false'}" for c in st["competencies"])
    if args.inline:
        transcript = "## Transcript (interviewer private notes removed)\n\n" + filtered
    else:
        fpath = packet_file(sdir, f"{inst['instance_id']}.transcript.md", filtered)
        transcript = f"## Transcript\n\nRead it with the Read tool (interviewer private notes already removed): {fpath}"
    notes = "\n".join(f"- {n}" for n in args.note or [])
    cause = {"external": "external (competencies without signal stay no_evidence)",
             "candidate": "candidate (score what was missing and list the uncovered signal points)"}.get(
        END_REASONS.get(inst.get("end_reason")), "unknown (infer from the final interviewer meta)")
    return f"""# Evaluator packet: {inst['instance_id']}

Score this one stage instance and return ONLY the scorecard markdown (final message, no preamble, no code fence).

## Config
- instance_id: {inst['instance_id']}
- stage: {inst['stage']}
- variant: {inst['variant']}
- target level: {session['level']}
- role: {session['role']}; domain: {session['domain']}
- session language: {session['lang']} ({LANGS[session['lang']]}); write the scorecard body in it, keep enums and ids in English
- session mode: {session.get('mode', 'normal')}
- rubric_version: {version}
- end_reason: {inst.get('end_reason') or '(none recorded: infer it from the final interviewer meta)'}
- end cause: {cause}

## Competencies to score (all of them, and no others)
{comps}

## Files (read with the Read tool)
- rubric: {rub}
- study map: {ctx.base / 'study-map.yaml'}
- scorecard template: {ctx.base / 'templates' / 'scorecard.md'}

{transcript}

## Notes from the orchestrator
{notes or '(none)'}

## Reminder
Quotes must be verbatim from candidate turns (turn_id = the number n of `T<n>`). Apply hint caps. Derive the recommendation with the fixed rule from the core flags above.
"""


def debrief_packet(ctx, cat, sdir, session, args) -> str:
    mode = args.mode
    role = session["role"]
    if mode == "cut" and not cat["roles"][role]["cut"]:
        raise SimError(f"role '{role}' has no cut")
    phases = PHASES[:2] if mode == "cut" else PHASES
    insts = [i for i in catalog_order(cat, session, session.get("instances") or []) if i["phase"] in phases]
    rows, missing, practice, skipped = [], [], [], []
    for i in insts:
        iid = i["instance_id"]
        w = weight_for(cat, role, i["stage"], i["variant"])
        if i["status"] == "skipped":
            skipped.append(iid)
            continue
        sc = scorecard_path(sdir, i)
        front = load_scorecard_front(sdir, i) if sc else None
        derived = None
        if front:
            derived = content.derive_recommendation(front.get("scores") or {}, core_ids(cat, i["stage"]))
        row = (f"| {iid} | {i['phase']} | {w} | {i['status']} | {i.get('end_reason') or '-'} | "
               f"{sc if sc else '(no scorecard)'} | {derived or '-'} |")
        if i["status"] != "done" or not sc:
            missing.append(iid)
        if is_practice(session, i):
            practice.append(iid)
        rows.append(row)
    vo1 = [i for i in insts if i["phase"] == "vo1"]
    sel_all = [i for i in session.get("instances") or [] if i["phase"] in phases]
    complete = (all(i["status"] == "done" for i in sel_all) and not missing
                and any(i["phase"] == "vo1" for i in sel_all))
    screens = [i["instance_id"] for i in insts if i["phase"] == "screen" and scorecard_path(sdir, i)]
    weights = cat["roles"][role].get("weights") or {}
    wtxt = "\n".join(f"- {k}: {v}" for k, v in weights.items())
    personas = "\n".join(f"- {s['id']}: {s['persona']['name']} ({s['persona']['title']})" for s in cat["stages"])
    cut = session.get("cut")
    return f"""# Debrief packet: {mode} ({session['id']})

Run the {mode} debrief and return ONLY the debrief markdown (final message, no preamble, no code fence).

## Session
- mode: {mode}
- session id: {session['id']}
- role: {role}; target level: {session['level']}; domain: {session['domain']}
- session language: {session['lang']} ({LANGS[session['lang']]})
- session mode: {session.get('mode', 'normal')}
- cut result: {yamlish.dumps(cut).strip().replace(chr(10), '; ') if cut else '(none)'}
- loop complete: {'true' if complete else 'false'} ({'every selected stage is done and evaluated' if complete else 'stages are missing, skipped, unevaluated or the phase is incomplete: mark the outcome provisional'})
- evaluated screens: {', '.join(screens) if screens else 'none (say so explicitly)'}
- practice-only instances (feedback only, not in the tally): {', '.join(practice) if practice else 'none'}
- skipped instances: {', '.join(skipped) if skipped else 'none'}
- missing or unevaluated: {', '.join(missing) if missing else 'none'}

## Scorecards in catalog order
`recommend` is the simulator's derived recommendation (authoritative).

| instance | phase | weight | status | end_reason | scorecard path | recommend |
|---|---|---|---|---|---|---|
{chr(10).join(rows) or '| (none) | | | | | | |'}

## Role weights (key stage@variant wins over stage)
{wtxt or '(none)'}

## Files (read with the Read tool; do not read rubric.md)
- catalog: {ctx.base / 'catalog.yaml'}
- study map: {ctx.base / 'study-map.yaml'}
- debrief template: {ctx.base / 'templates' / 'debrief.md'}
- transcripts (optional, to check context of an already quoted piece of evidence): {sdir / 'transcripts'}

## Interviewer personas
{personas}
"""


def ai_pair_packet(ctx, cat, sdir, session, inst) -> str:
    pid = inst.get("problem_id")
    dirname, path = locate_material(ctx, inst["stage"], pid) if pid else (None, None)
    if dirname != "repos":
        raise SimError("this instance has no repo selected (run `select` on an ai-assisted-coding instance first)")
    work = (sdir / "work" / inst["instance_id"]).resolve()
    fl = path / "flaws.yaml"
    flaws = (yamlish.loads(read_text(fl)) or {}).get("flaws") or [] if fl.is_file() else []
    keep = [{k: f.get(k) for k in ("id", "zone", "trigger_keywords", "description")} for f in flaws]
    leaked = [n for n in ("flaws.yaml", "hidden", "notes.md") if (work / n).exists()]
    if leaked:
        raise SimError(f"workspace contains interviewer-only files: {', '.join(leaked)}", 1)
    return ("<orchestrator private>\n"
            f"workspace: {work}\n"
            f"language: {session['lang']} ({LANGS[session['lang']]})\n"
            + (yamlish.dumps({"flaws": keep}) if keep else "flaws: []\n")
            + "</orchestrator>\n")


def cmd_packet(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    sdir, session = resolve_session(ctx, args.session)
    ensure_writable(ctx)
    if args.kind == "debrief":
        if not args.mode:
            raise SimError("packet debrief needs --mode cut|final")
        text = debrief_packet(ctx, cat, sdir, session, args)
        path = packet_file(sdir, f"debrief-{args.mode}.md", text)
    else:
        if not args.instance:
            raise SimError(f"packet {args.kind} needs an instance (packet {args.kind} <session> <NN>)")
        inst = get_instance(session, args.instance)
        if args.kind == "evaluator":
            text = evaluator_packet(ctx, cat, sdir, session, inst, args)
            path = packet_file(sdir, f"{inst['instance_id']}.evaluator.md", text)
        else:
            text = ai_pair_packet(ctx, cat, sdir, session, inst)
            path = packet_file(sdir, f"{inst['instance_id']}.ai-pair.md", text)
    emit(args, {"kind": args.kind, "packet_path": path, "packet": text}, text)
    return 0


# ---------------------------------------------------------------- progress
SCORE_LABEL = {"SN": "SN", "N": "N", "Y": "Y", "SY": "SY", "no_evidence": "n/e"}


def collect_points(ctx: Ctx) -> dict:
    series: dict = {}
    for sdir, sess in list_sessions(ctx):
        for order, inst in enumerate(sess.get("instances") or []):
            front = load_scorecard_front(sdir, inst)
            if not front:
                continue
            practice = is_practice(sess, inst)
            for comp, score in (front.get("scores") or {}).items():
                key = (inst["stage"], inst["variant"], comp)
                series.setdefault(key, []).append({
                    "date": str(sess.get("created", ""))[:10], "session": sess.get("id", sdir.name),
                    "created": str(sess.get("created", "")), "order": order,
                    "level": front.get("level") or sess.get("level"), "rubric": front.get("rubric_version"),
                    "score": score, "practice": practice})
    return series


def load_scorecard_front(sdir: Path, inst: dict):
    ref = inst.get("scorecard")
    path = (sdir / ref) if ref and not Path(str(ref)).is_absolute() else Path(str(ref)) if ref else sdir / "scorecards" / f"{inst['instance_id']}.md"
    if not path.is_file():
        path = sdir / "scorecards" / f"{inst['instance_id']}.md"
    if not path.is_file():
        return None
    try:
        return yamlish.split_front_matter(read_text(path))[0]
    except yamlish.YamlError:
        return None


def render_progress(series: dict, generated: str) -> str:
    out = ["# Progress", "", f"_Generated {generated} from local sessions. `n/e` = no evidence (not a low score). "
           "Practice sessions are marked. A level or rubric-version change breaks comparability._", ""]
    last_stage = last_variant = None
    for (stage, variant, comp) in sorted(series):
        if stage != last_stage:
            out += [f"## {stage}", ""]
            last_stage, last_variant = stage, None
        if variant != last_variant:
            out += [f"### {variant}", ""]
            last_variant = variant
        out += [f"#### {comp}", "", "| Date | Session | Level | Rubric | Score | Trend | Notes |", "|---|---|---|---|---|---|---|"]
        out += progress_rows(sorted(series[(stage, variant, comp)], key=lambda p: (p["created"], p["order"])))
        out.append("")
    if len(out) == 4:
        out.append("No scorecards yet.")
    return "\n".join(out) + "\n"


def progress_rows(points: list[dict]) -> list[str]:
    rows, prev = [], None
    for p in points:
        notes = []
        if p["practice"]:
            notes.append("practice")
        if p["score"] == "no_evidence":
            notes.append("no evidence")
        comparable = prev is not None and prev["level"] == p["level"] and prev["rubric"] == p["rubric"]
        if prev is not None and prev["level"] != p["level"]:
            notes.append(f"level change {prev['level']}->{p['level']} (not comparable)")
        if prev is not None and prev["rubric"] != p["rubric"]:
            notes.append(f"rubric v{prev['rubric']}->v{p['rubric']} (not comparable)")
        trend = "-"
        if comparable and p["score"] in content.SCORE_RANK and prev["score"] in content.SCORE_RANK:
            diff = content.SCORE_RANK[p["score"]] - content.SCORE_RANK[prev["score"]]
            trend = "up" if diff > 0 else "down" if diff < 0 else "same"
        rows.append(f"| {p['date']} | {p['session']} | {p['level']} | v{p['rubric']} | {SCORE_LABEL.get(p['score'], p['score'])} | {trend} | {'; '.join(notes)} |")
        if p["score"] in content.SCORE_RANK:
            prev = p
        elif prev is not None and (prev["level"], prev["rubric"]) != (p["level"], p["rubric"]):
            prev = p
    return rows


def cmd_progress(ctx: Ctx, args) -> int:
    series = collect_points(ctx)
    text = render_progress(series, ctx.now().strftime("%Y-%m-%d"))
    if not args.no_write:
        ensure_writable(ctx)
        atomic_write(ctx.sessions / "PROGRESS.md", text)
    emit(args, {"series": len(series), "path": str(ctx.sessions / "PROGRESS.md"), "markdown": text}, text)
    return 0


# ------------------------------------------------------------ state / info
def state_data(ctx: Ctx, cat: dict, sdir: Path, session: dict) -> dict:
    insts = []
    for i in session.get("instances") or []:
        row = {k: i.get(k) for k in ("instance_id", "phase", "status", "end_reason", "attempt", "agent_name",
                                     "question_ids", "problem_id", "scorecard")}
        row.update(clock(ctx, cat, session, i))
        row["turns"] = len(read_turns(transcript_path(sdir, i)))
        insts.append(row)
    cfg = {k: session.get(k) for k in ("id", "role", "level", "lang", "domain", "time_scale", "python",
                                       "env_ephemeral", "feedback", "mode", "cut", "final")}
    return {"path": str(sdir), "config": cfg, "instances": insts}


def cmd_state(ctx: Ctx, args) -> int:
    cat = load_catalog(ctx)
    if args.pending:
        rows = []
        for sdir, sess in reversed(list_sessions(ctx)):
            open_i = [i["instance_id"] for i in sess.get("instances") or [] if i["status"] in ("pending", "in_progress")]
            if open_i:
                rows.append({"session": sess["id"], "created": sess.get("created"), "role": sess.get("role"),
                             "pending": open_i,
                             "in_progress": [i["instance_id"] for i in sess["instances"] if i["status"] == "in_progress"]})
        emit(args, {"pending_sessions": rows}, "\n".join(f"{r['session']} ({r['role']}): in_progress={r['in_progress']} pending={r['pending']}" for r in rows) or "no pending sessions")
        return 0
    sdir, session = resolve_session(ctx, args.session or "latest")
    if args.time:
        return state_time(ctx, cat, session, args)
    data = state_data(ctx, cat, sdir, session)
    lines = [f"session {session['id']}: " + " ".join(f"{k}={v}" for k, v in data["config"].items() if k != "id" and v is not None)]
    for r in data["instances"]:
        lines.append(f"  {r['instance_id']} [{r['phase']}] {r['status']} t={r['t_min']}m/{r['budget_min']}m ({r['pct']}%) turns={r['turns']} attempt={r['attempt']}")
    emit(args, data, "\n".join(lines))
    return 0


def state_time(ctx: Ctx, cat: dict, session: dict, args) -> int:
    """`state --time`: scaled elapsed active minutes vs. budget of one instance (used by ::time)."""
    insts = session.get("instances") or []
    if args.instance:
        inst = get_instance(session, args.instance)
    else:
        open_i = [i for i in insts if i["status"] == "in_progress"] or [i for i in insts if i["status"] == "pending"]
        if not open_i:
            raise SimError("no open instance in this session; pass --instance NN")
        inst = open_i[0]
    clk = clock(ctx, cat, session, inst)
    remaining = max(0, clk["budget_min"] - clk["t_min"])
    data = {"instance": inst["instance_id"], "status": inst["status"], **clk, "remaining_min": remaining}
    emit(args, data, f"{inst['instance_id']}: t={clk['t_min']}m of {clk['budget_min']}m ({clk['pct']}%), "
                     f"about {remaining}m left (active time only, time_scale={clk['time_scale']})")
    return 0


def cmd_info(ctx: Ctx, args) -> int:
    ephemeral = os.environ.get("CLAUDE_CODE_REMOTE") == "true"
    g = guard(ctx)
    data = {"python_version": sys.version.split()[0], "executable": sys.executable, "platform": sys.platform,
            "working_command": detect_python(), "candidates": {c: bool(shutil.which(c)) for c in ("python", "python3", "py")},
            "git": bool(shutil.which("git")), "claude_code_remote": os.environ.get("CLAUDE_CODE_REMOTE"),
            "env_ephemeral": ephemeral, "warning": EPHEMERAL if ephemeral else None,
            "base": str(ctx.base), "sessions_dir": str(ctx.sessions), "guard": g}
    lines = [f"python {data['python_version']} at {data['executable']} ({data['platform']})",
             f"working command: {data['working_command']}  (found: {[c for c, ok in data['candidates'].items() if ok]})",
             f"git: {'available' if data['git'] else 'missing'}; guard: {g['status']}",
             f"CLAUDE_CODE_REMOTE={data['claude_code_remote']!r}"]
    if ephemeral:
        lines.append("warning: " + EPHEMERAL)
    emit(args, data, "\n".join(lines))
    return 0


# -------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--base", help="netflix-ml-interview directory (default: next to this script)")
    common.add_argument("--now", help="override the clock (ISO 8601 UTC), for tests")
    p = argparse.ArgumentParser(prog="sim.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_, session=True, instance=True):
        sp = sub.add_parser(name, parents=[common], help=help_)
        if session:
            sp.add_argument("session", help="session id, short id, path or 'latest'")
        if instance:
            sp.add_argument("instance", help="instance id (or its NN prefix)")
        sp.set_defaults(fn=fn)
        return sp

    add("guard", cmd_guard, "check that sessions are git-ignored and untracked", False, False)
    new = add("new", cmd_new, "create a session", False, False)
    new.add_argument("--role", required=True)
    new.add_argument("--level", default="L5")
    new.add_argument("--lang", default="en")
    new.add_argument("--domain")
    new.add_argument("--stages", help="full|screen|vo1|vo2|stage|stage@variant, comma separated (default: full)")
    new.add_argument("--order", choices=("canonical", "given"), default="canonical")
    new.add_argument("--feedback", default="immediate")
    new.add_argument("--time-scale", type=float, default=1.5)
    new.add_argument("--python", help="python command that works (default: autodetect)")
    new.add_argument("--background", help="path to the candidate background file")
    new.add_argument("--dry-run", action="store_true",
                     help="validate everything against the catalog and print the resolved plan; creates nothing")
    sel = add("select", cmd_select, "choose questions/material and print the launch packet")
    sel.add_argument("--seed", type=int, default=0)
    sel.add_argument("--count", type=int, help="number of main questions")
    sel.add_argument("--reselect", action="store_true", help="ignore previous selection")
    turn = add("turn", cmd_turn, "record a candidate turn and print the message for the interviewer")
    turn.add_argument("--text")
    turn.add_argument("--file")
    turn.add_argument("--stdin", action="store_true")
    turn.add_argument("--note", action="append", help="extra orchestrator line (e.g. a tests result)")
    log = add("log", cmd_log, "append an interviewer/ai-pair/orchestrator message to the transcript")
    log.add_argument("--role", choices=("interviewer", "ai-pair", "orchestrator"), default="interviewer")
    log.add_argument("--text")
    log.add_argument("--file")
    log.add_argument("--stdin", action="store_true")
    log.add_argument("--accept-malformed", action="store_true", help="store a malformed reply raw (after one retry)")
    add("pause", cmd_pause, "close the open time segment")
    end = add("end", cmd_end, "finish an instance")
    end.add_argument("--reason", required=True, choices=sorted(END_REASONS))
    st = add("set", cmd_set, "set allowed fields: key=value (value may be @file)", True, False)
    st.add_argument("--instance")
    st.add_argument("pairs", nargs="+")
    rt = add("run-tests", cmd_run_tests, "run problem/repo tests (and candidate tests)")
    rt.add_argument("--timeout", type=int, default=30)
    rt.add_argument("--hidden", action="store_true", help="also run hidden flaw tests (ai-assisted-coding)")
    rt.add_argument("--no-log", action="store_true")
    ap = add("apply", cmd_apply, "apply a unified diff to the session workspace")
    ap.add_argument("--file")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--text")
    ap.add_argument("--check", action="store_true", help="dry run")
    ap.add_argument("--no-log", action="store_true")
    ve = sub.add_parser("verify-scorecard", parents=[common], help="verify evidence quotes and rules of a scorecard")
    ve.add_argument("--session")
    ve.add_argument("--instance")
    ve.add_argument("--scorecard")
    ve.add_argument("--transcript")
    ve.add_argument("--downgrade", action="store_true", help="set unverifiable competencies to no_evidence")
    ve.set_defaults(fn=cmd_verify)
    add("rebuild", cmd_rebuild, "print the prompt to relaunch an interviewer (attempt+1)")
    tr = add("transcript", cmd_transcript, "print a transcript")
    tr.add_argument("--for-evaluator", action="store_true", help="strip notes_private")
    tr.add_argument("--out")
    ws = add("write-scorecard", cmd_write_scorecard, "write the evaluator's scorecard, validate it and verify its quotes")
    ws.add_argument("--text")
    ws.add_argument("--file")
    ws.add_argument("--stdin", action="store_true")
    ws.add_argument("--keep-invalid", action="store_true", help="keep the file even if checks fail (exit code stays 1)")
    ws.add_argument("--downgrade", action="store_true",
                    help="final attempt: set unverifiable competencies to no_evidence and recompute the recommendation")
    wd = sub.add_parser("write-debrief", parents=[common], help="write and validate a cut/final debrief")
    wd.add_argument("session")
    wd.add_argument("--mode", required=True, choices=("cut", "final"))
    wd.add_argument("--text")
    wd.add_argument("--file")
    wd.add_argument("--stdin", action="store_true")
    wd.add_argument("--reason", help="short reason stored in session.yaml cut.reason (cut mode)")
    wd.add_argument("--keep-invalid", action="store_true")
    wd.set_defaults(fn=cmd_write_debrief)
    pk = sub.add_parser("packet", parents=[common], help="print the exact prompt for evaluator, debrief or ai-pair agents")
    pk.add_argument("kind", choices=("evaluator", "debrief", "ai-pair"))
    pk.add_argument("session")
    pk.add_argument("instance", nargs="?", help="instance (evaluator, ai-pair)")
    pk.add_argument("--mode", choices=("cut", "final"), help="debrief mode")
    pk.add_argument("--inline", action="store_true", help="evaluator: embed the filtered transcript instead of its path")
    pk.add_argument("--note", action="append", help="evaluator: extra factual line (e.g. hidden-test result)")
    pk.set_defaults(fn=cmd_packet)
    rc = sub.add_parser("recommend", parents=[common], help="derive the recommendation of a scorecard")
    rc.add_argument("scorecard")
    rc.set_defaults(fn=cmd_recommend)
    stt = sub.add_parser("state", parents=[common], help="show session state and clocks")
    stt.add_argument("session", nargs="?")
    stt.add_argument("--pending", action="store_true", help="list sessions with open instances")
    stt.add_argument("--time", action="store_true", help="only elapsed active minutes (scaled), budget and percentage")
    stt.add_argument("--instance", help="with --time: instance (default: the one in progress)")
    stt.set_defaults(fn=cmd_state)
    pr = sub.add_parser("progress", parents=[common], help="regenerate sessions/PROGRESS.md")
    pr.add_argument("--no-write", action="store_true")
    pr.set_defaults(fn=cmd_progress)
    inf = sub.add_parser("info", parents=[common], help="environment info")
    inf.set_defaults(fn=cmd_info)
    return p


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    ctx = Ctx(args.base, args.now)
    try:
        return args.fn(ctx, args)
    except SimError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
    except (yamlish.YamlError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
