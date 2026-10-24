---
variant: sql-pandas
roles: [ds]
levels: [L4, L5, L6]
title: Monthly cohort retention
minutes: 35
---
# Monthly cohort retention

Tables (SQLite):

```sql
signups(user_id INTEGER PRIMARY KEY, signup_date TEXT)          -- 'YYYY-MM-DD'
activity(user_id INTEGER, activity_date TEXT)                  -- one row per day with any viewing; may repeat
```

Implement `cohort_retention_query()` returning one SQL string (no parameters) with columns:

`cohort_month, month_offset, active_users, cohort_size, retention`

- `cohort_month`: signup month as `'YYYY-MM'`.
- `month_offset`: whole calendar months between the signup month and the activity month (0 = the signup month).
- `active_users`: **distinct** users of the cohort with any activity in that offset month.
- `cohort_size`: number of users that signed up in the cohort month (also those with no activity at all).
- `retention`: `active_users / cohort_size` as a float rounded to 4 decimals.
- Ignore activity dated before the signup date, and activity from users that are not in `signups`.
- Return only offsets that have at least one active user; order by `cohort_month`, `month_offset`.

Write your own checks: what happens to a user who signs up on the 31st, or never returns?
