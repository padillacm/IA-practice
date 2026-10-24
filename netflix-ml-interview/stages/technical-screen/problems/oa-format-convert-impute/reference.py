from collections import Counter


def _missing(v):
    return v is None or v == ""


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _plan(records):
    cols = sorted({k for r in records for k in r})
    plan = {}
    for c in cols:
        vals = [r[c] for r in records if c in r and not _missing(r[c])]
        if not vals:
            continue
        if all(_is_num(v) for v in vals):
            fill = sum(vals) / len(vals)
        else:
            counts = Counter(vals)
            top = max(counts.values())
            fill = min((v for v, n in counts.items() if n == top), key=str)
        plan[c] = fill
    return plan


def to_columns(records):
    plan = _plan(records)
    out = {}
    for c, fill in plan.items():
        out[c] = [fill if (c not in r or _missing(r[c])) else r[c] for r in records]
    return out


def impute_summary(records):
    plan = _plan(records)
    return {c: fill for c, fill in plan.items() if any(c not in r or _missing(r[c]) for r in records)}
