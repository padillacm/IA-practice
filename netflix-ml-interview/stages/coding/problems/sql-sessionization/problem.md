---
variant: sql-pandas
roles: [ds]
levels: [L4, L5, L6]
title: Sessionization of playback events
minutes: 35
---
# Sessionization of playback events

Table (SQLite):

```sql
events(user_id INTEGER, ts INTEGER, event TEXT)   -- ts: unix seconds; events may have equal ts
```

A **session** is a maximal run of one user's events in which consecutive events are at most 1800 seconds apart
(a gap of **more than** 1800 s starts a new session).

Implement `sessionize_query()` returning one SQL string (no parameters) with columns:

`user_id, session_num, start_ts, end_ts, n_events`

- `session_num` starts at 1 for each user and increases with time.
- Events with equal `ts` for the same user belong to the same session.
- Order by `user_id`, `session_num`.

Use window functions (`LAG` plus a running `SUM`). Write your own checks; which timestamps sit exactly on the boundary?
