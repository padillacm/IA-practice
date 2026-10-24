# Follow-ups: sessionization

1. **Extra rules.** Cap the session length at 6 hours, or start a new session on a new device. Why can't the running
   SUM express the cap directly, and what are the options (recursive CTE, a Python UDF, pandas loop)?
2. **Scale.** 5 trillion events per year: the window needs data sorted by (user_id, ts). Partition by user (parallel
   workers per hash bucket), process one day at a time and carry the last event per user into the next day. Is the
   sessionization incremental? What about sessions that cross midnight?
3. **Late and duplicate events.** Duplicate delivery makes `n_events` wrong, late events can merge two sessions. How do
   you deduplicate (event ids) and recompute only affected users?
4. **Concurrency.** A streaming job and the daily batch both write sessions. What goes wrong if they disagree and how do
   you pick a single source of truth (idempotent upsert keyed by user and session start)?
5. **Pandas.** `groupby('user_id').ts.diff().gt(1800).cumsum()` per user. Beware that the cumsum must restart per
   user; show the groupby-transform.
6. **Choice of threshold.** How would you pick 1800 s from data (inter-event gap distribution is bimodal) and why does
   the threshold change downstream metrics?
