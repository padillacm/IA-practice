# Follow-ups: monthly cohort retention

1. **Definition.** Calendar-month offsets vs rolling 30-day windows (day-N retention). Which would you use for a
   subscription product and why? Rewrite with `julianday` differences.
2. **Missing zero cells.** The query omits offsets with no active users. How do you produce a full triangle
   (cross join of cohorts and offsets), and cut offsets that have not happened yet (right-censoring)?
3. **Scale.** `activity` has 200 billion rows. Pre-aggregate to (user, month) once per day incrementally instead of
   joining raw rows; partition by month; the join is on user_id, so shard by user_id and run shards in parallel.
   Where does DISTINCT hurt?
4. **Concurrency and consistency.** A backfill rewrites a month of `activity` while dashboards read the table. How do you
   publish atomically (write a new partition, then swap) so readers never see half of a month?
5. **Interpretation.** Survivor bias and a mix shift between cohorts (a promotion-driven cohort). What other views would
   you add before telling a PM that retention "improved"?
6. **Pandas.** Same logic with `merge`, `dt.to_period('M')`, `drop_duplicates` and `groupby.nunique`.
