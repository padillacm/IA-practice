# Expected findings: rolling watch features (interviewer only)

All tests pass because the fixture has two members, one event each in the same implied timezone, no duplicates, no
impressions on the same day as a play, and a handful of rows. Production breaks it as follows.

## Findings (severity in brackets)

1. **[critical] Label leakage through day-level comparison.** `played_at.dt.normalize() <= label_ts.dt.normalize()` keeps
   every play on the label's calendar day, including plays after the impression. When `clicked = 1` the play caused by the
   click is in the events table, so `watch_minutes_7d` and `days_since_last_play = 0` encode the label. Offline AUC will be
   inflated and the online model collapses. Fix: strict event-time comparison `played_at < label_ts` (use `<` and the exact
   timestamps, not dates), and cap the window start to `label_ts - 7 days`.
2. **[critical] Timezone and event-time mismatch.** `label_ts` is UTC and `played_at` is naive device-local time;
   `tz_localize(None)` just drops the UTC label and the two naive values are then compared as if they were the same zone.
   Window boundaries are off by the member's UTC offset (up to 14 h), plays can appear to be in the future (leakage) or
   missing, and DST shifts them again. Fix: convert client times to UTC with the device offset logged at play time (or use
   a server-side event time), keep everything tz-aware UTC.
3. **[high] Training/serving skew.** The online store keeps UTC-day buckets with a few minutes of lag; offline is a
   168-hour window ending at the impression. A "7 day" window online is 6 full buckets plus a partial day, and misses plays
   of the last minutes. `fillna(0)` for `days_since_last_play` encodes "no history" as "played today" (offline
   `0` means the member played within 24 h), whereas online a missing key may yield null or -1. Fix: one shared feature
   definition, an explicit sentinel/`has_history` flag, and log the served feature values at inference time for training
   (feature logging) instead of recomputing them offline.
4. **[high] Unbounded join.** `labels.merge(events, on="user_id")` materializes (labels per member x events per member)
   rows before filtering. A heavy member with 20k impressions and 30k plays creates 600M rows; the 64 GB machine OOMs on a
   real day although the test never notices. Fix: pre-aggregate events to member-day (or member-hour) buckets, then do a
   range join / as-of join / rolling window sorted by time, or push the work to the warehouse or Spark with a bounded
   window function.
5. **[medium] Mutates caller inputs.** `events["played_at"] = ...` and `labels["label_ts"] = ...` change the DataFrames
   passed in; the second call in the same process sees different dtypes. Copy first.
6. **[medium] Non-deterministic / missing keys.** `groupby(["user_id","label_ts"])` merges two impressions with the same
   second into one row, and the final left merge duplicates rows when `labels` has duplicate `(user_id, label_ts)`.
   Use a unique impression id as the key.
7. **[low] Window semantics unclear.** Inclusive start day means 8 calendar days on some labels. Name the unit and test the
   boundary (exactly 7 days before).
8. **[low] Missing tests.** No test for same-day future plays, timezone offsets, a member with no history, duplicate
   impressions, or a heavy-member scale test.

A candidate who finds 1, 2 and 4 on their own is at the L5 bar; finding 3 (skew) without being prompted is a strong
signal. Findings 5 to 8 are optional.

## Hint ladder (use one step at a time and record it)
1. "Walk me through one member with a click: which rows end up inside the window?"
2. "Where do `label_ts` and `played_at` come from, and are they in the same timezone?"
3. "How many rows does the merge produce for a member with 10k impressions and 10k plays?"
4. "How would the online store compute this number?"

## Serving follow-up (about 10 min)
Ask: "These three features must also be available at request time for the homepage ranker, but a nightly batch also
needs them for 40M labels. How do you serve them?" Look for:
- Tiering by freshness requirement: precomputed batch features in a key-value store (hours of staleness acceptable) for
  stable aggregates; streaming updates of per-member time-bucketed counters for minutes-level freshness; request-time
  context features computed in the service with millisecond budget.
- One definition used offline and online (shared transform library or feature store), point-in-time correct training
  data, and logging of served features to train on what the model actually saw.
- Latency and availability: p99 budget, fallbacks and defaults when the store is down or a key is missing, TTLs,
  backfill when a feature definition changes, and how to roll out (shadow, then interleaving, then A/B).
- Monitoring: online/offline distribution comparison per feature, missing-rate alerts, freshness lag.

## Level notes
- L4: finds the leakage or the memory issue with a hint, proposes a sensible fix, mentions skew only when asked.
- L5: finds leakage, timezone and the join explosion unprompted, ranks them by impact, and describes the shared
  definition plus feature logging for serving.
- L6: also designs the tiered serving, the rollout and the monitoring, and states what review process would have caught
  the issue (point-in-time test, scale test in CI).
