# Interviewer notes (private - never show to the candidate)

Repo: offline_eval (logged-impression evaluation with time-based holdout and popularity baseline). One flaw: future-leakage.

## What the workspace already gets right (do not treat as bugs)
- Duplicate deliveries are removed by impression_id (not by user+item, which would wrongly drop repeat exposures).
- Split is strictly ts < cutoff for history and ts >= cutoff for evaluation.
- NDCG uses the ideal from the full slate; requests with no clicks are skipped (documented in the module docstring).

## What good looks like
- Decomposition: window filter in popularity_counts first, then thread it through run_eval, then the per-day report as a grouping layer over existing slate evaluation (reuse, do not copy the loop).
- Prompting: states the interval `[cutoff - window, cutoff)` explicitly; tells the AI to keep dedupe and split intact; asks for tests including a boundary at `cutoff - window` (inclusive) and `cutoff` (exclusive).
- Verification: asks "can the baseline see anything at or after the cutoff?" and writes a test with a future-only item; checks that the default (no window) output is unchanged on the existing fixture.
- Pushback: catches an anchor on max(ts) or dropped upper bound (flaw future-leakage), explains the optimistic-lift consequence, asks for a fix.
- Extension: day buckets with sparse days, bootstrap CIs per day, position-bias in logged data (logging policy vs evaluated policy), counterfactual estimators.

## Flaw timing
- Triggered on a trailing-window / window prompt. A candidate who states the half-open interval in the prompt often gets a correct diff: record flaws_triggered as empty in that case and note it as strong prompting.
- Existing tests do not catch the flaw; only a test with post-cutoff clicks does.

## Probes if the candidate is quiet
- "If this ships and offline lift jumps 40%, what would you check first?"
- "How do you know the baseline in this report is fair to the logged policy?"
- Culture hook: ask what they would tell a teammate who wants to merge a green-test AI diff without reading it (candor/judgment).
