# Expected findings: backfill of title popularity (interviewer only)

The test passes because it runs once, on one day, with one history row per title, and checks two numbers. Production
breaks it as follows.

## Findings (severity in brackets)

1. **[critical] Non-idempotent write.** `to_sql(..., if_exists="append")` appends. A retry after a partial failure or a
   second backfill run duplicates every day already written; two concurrent runs interleave duplicates. Downstream
   `SUM(plays)` doubles. Fix: write per-date partitions with delete-then-insert in one transaction, `MERGE`/upsert keyed on
   `(day, title_id)`, or write to a staging table and atomically swap the partition; make the job safe to re-run.
2. **[critical] Join fan-out on a slowly changing dimension.** `titles_history` has several rows per title; the inner merge
   multiplies each title row by its number of history rows, so `plays` is inflated for re-tagged titles, and
   `groupby().max()` normalization is distorted. The inner join also silently drops titles with no metadata row. Fix: pick
   the single metadata row valid on `day` (as-of join), assert one row per title after the join, and use a left join
   with a check for dropped keys.
3. **[critical] Leakage and non-determinism from `overall` and `computed_at`.** `overall` is the mean of the whole
   destination table, including days after `day` when backfilling history (future data), and changes after every run, so
   results depend on the order of days and on reruns. `fillna(overall)` is also dead code after an inner merge, hiding that
   missing values were not handled. `computed_at = utcnow()` stamps backfilled rows as if known today: a point-in-time
   join by `computed_at` leaks the 18 months of history into the past (or drops it). Fix: compute from data available at
   the end of `day` only, store `as_of`/`valid_from = day + lag` separately from `computed_at`.
4. **[high] Training/serving skew in `title_code`.** `LabelEncoder().fit_transform` is fit per day on that day's titles, so
   the integer for the same title changes between days (and between the batch table and the online service). Fix: a
   stable, versioned vocabulary (hash or a persisted id map), never refit per partition.
5. **[high] `pop_norm` is relative to that day's max.** One viral title makes everything else near 0; online the service uses
   a trailing-window max, so the scales differ. Also divides by zero for an empty day (`max()` of an empty frame is NaN, then
   fails downstream). Fix: normalize with a documented, serveable statistic (log counts, percentile rank within the day) and
   handle empty days.
6. **[medium] Scale and memory.** One query per day pulls raw `plays` rows (1.2B per day) into pandas just to count them.
   Aggregate in the warehouse (`GROUP BY title_id`) and read only the counts; 18 months x full-day pulls is 550 sequential
   days with no parallelism or checkpointing.
7. **[medium] SQL built with f-strings and no late-data handling.** The date is formatted into the query (injection risk if
   the range ever comes from a request), and plays arriving after midnight are missed for a day that was already written;
   `end` can be today, producing a partial day treated as final.
8. **[low] Test gaps.** No test for rerun, concurrency, multiple metadata rows, empty day, or the stability of codes across
   days.

L5 finds 1, 2 and 3 (or 4) unprompted. Finding 3's point-in-time aspect and 4's skew are strong-signal items.

## Hint ladder
1. "What happens if the orchestrator retries this task after it wrote half the range?"
2. "How many rows does `titles_history` have for a title that was re-tagged twice?"
3. "Is the integer for title 42 the same on March 1st and March 2nd?"
4. "What data does `overall` read when you backfill last year?"

## Serving follow-up (about 10 min)
Ask: "The cold-start ranker needs these features at request time with a p99 of 20 ms, the nightly trainer needs
point-in-time-correct history, and a dashboard needs them within the hour. How do you serve each?" Look for:
- A partitioned, idempotent batch table as the source of truth for training with `as_of` semantics; a key-value store
  loaded from the latest partition for request-time lookups, with a version and TTL; a streaming increment path only if
  the freshness requirement demands it, reconciled by the batch.
- Atomic publish (write the new partition, flip a pointer) so a reader never sees a partial day; fallbacks when the
  latest day is missing (use yesterday plus a staleness flag).
- Stable ids and normalization shared across batch and online, versioned feature definitions, and backfills that do not
  rewrite the history that already trained a deployed model without a version bump.
- Monitoring: row count per partition vs expectation, duplicate-key checks, distribution drift of `pop_norm`, freshness SLO.

## Level notes
- L4: finds duplicate rows on rerun and the join fan-out with a hint; fixes with delete-then-insert.
- L5: finds idempotency, fan-out and the point-in-time/leakage problem unprompted and proposes concrete fixes; raises the
  `title_code` skew when discussing serving.
- L6: designs the atomic-publish plus versioned-definition process, addresses concurrent runs with a lock or
  partition ownership, and names the checks that belong in the job (row-count and uniqueness assertions).
