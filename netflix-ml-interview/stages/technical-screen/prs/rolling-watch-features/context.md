# PR context: rolling watch features for the title-click ranker

Shown to the candidate together with `pr.diff`. Do not show `issues.md`.

**Title:** Add 7-day rolling watch features to the click-ranker training set

**Author:** a teammate on the personalization-ML team (you are the reviewer).

**Description:**
> Adds `watch_minutes_7d`, `distinct_titles_7d` and `days_since_last_play` for the click ranker's training data build.
> For each impression label we aggregate the member's plays in the previous 7 days. Unit test added; CI is green.
> The serving team will port the same logic to the online path next sprint, so I kept the function readable rather than
> fast. We expect about 40M labels per daily training build.

**Environment facts the interviewer may share when asked:**
- Impression labels (`label_ts`) are logged server side in UTC. Play events come from client logs; `played_at` is the
  device's local time as a string without offset. Members are worldwide.
- The events table is about 3 billion rows per 30 days; a heavy member can have thousands of plays and tens of thousands of
  impressions in a day.
- `clicked = 1` means the member started a play from that impression; that play is itself written to the events table with
  a `played_at` a few seconds after `label_ts`.
- The training job runs on a single 64 GB machine with pandas today.
- Online, the feature is served from a key-value store that holds per-member daily buckets (minutes and title ids per UTC
  day), updated by a stream job with up to a few minutes of lag.

**Format of the session (about 30 min of the PR part):** the candidate reads the diff, narrates concerns, ranks them,
and says what they would ask the author to change before merging. Then discuss serving (see `issues.md`).
