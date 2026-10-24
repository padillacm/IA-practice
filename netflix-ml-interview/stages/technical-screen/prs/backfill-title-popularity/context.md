# PR context: backfill of daily title popularity features

Shown to the candidate together with `pr.diff`. Do not show `issues.md`.

**Title:** Add backfill job for `title_popularity_daily`

**Author:** a teammate on the ML-platform team (you are the reviewer).

**Description:**
> Recomputes the daily popularity features (plays, normalized popularity, title code, genre) for a date range and writes
> them to `title_popularity_daily`, which feeds the cold-start ranker and a nightly retraining job. We need to backfill 18
> months because the definition of "play" changed. CI is green. I plan to run it for the whole range tonight, and rerun it
> if it fails halfway.

**Environment facts the interviewer may share when asked:**
- `plays` has about 1.2 billion rows per day; `title_popularity_daily` is read by training jobs and by a service that
  loads the latest day into memory.
- `titles_history` is a slowly changing dimension: one row per title per `valid_from` period (titles are re-tagged, so a
  title may have several rows).
- The job is run by an orchestrator that retries failed tasks automatically and sometimes runs two tasks for the same
  date range at once during manual re-triggers.
- The online ranker receives `title_code` as an integer feature.
- Training reads the table "as of" each training example's date and expects the values that would have been known then.

**Format of the session (about 30 min of the PR part):** the candidate reads the diff, narrates concerns, ranks them, and
says what they would ask the author to change before merging. Then discuss serving (see `issues.md`).
