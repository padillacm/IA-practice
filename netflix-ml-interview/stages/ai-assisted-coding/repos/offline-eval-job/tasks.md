# Task: trailing-window popularity baseline and a per-day report

You own `offline_eval`, a small job that compares the logged ranking of a recommender against a
popularity baseline on a time-based holdout. Rows are logged impressions (one per item shown); the
logging pipeline is at-least-once. Code is in `workspace/`; run `python -m unittest` from that directory.

You may use the AI pair (`::ai <prompt>`). It proposes diffs; nothing is applied until `::apply`.
You are responsible for what you apply and for the numbers the job reports.

## Part 1 - trailing-window baseline

The baseline currently counts clicks over ALL history before the cutoff, so old hits dominate. Add an
optional `window` (seconds) to `run_eval` and `popularity_counts`: when given, only clicks in
`[cutoff_ts - window, cutoff_ts)` count. Default behavior (no window) must not change.

## Part 2 - per-day report

Add `run_eval_by_day(rows, cutoff_ts, k, day_seconds=86400)` that returns the same metrics for each
day of the evaluation period (day index = (ts - cutoff_ts) // day_seconds), plus the overall result.

## Expectations

- Add tests for what you build.
- Be ready to say how you know the reported lift is not inflated.
