---
variant: sql-pandas
roles: [ds]
levels: [L4, L5, L6]
title: Top titles by 7-day completions per country (window functions)
minutes: 30
---
# Top titles by 7-day completions per country

Table (SQLite):

```sql
plays(play_id INTEGER PRIMARY KEY, user_id INTEGER, title_id INTEGER, country TEXT,
      play_date TEXT,        -- 'YYYY-MM-DD'
      completed INTEGER)     -- 1 if the member finished the title, else 0
```

Implement `top_titles_query()` returning one SQL string with two named parameters, `:as_of` (a date string) and `:n`.
For the 7-day window ending at `:as_of` (inclusive, so `as_of - 6 days` through `as_of`), return for every country its
top `:n` titles by number of **completed** plays:

`country, title_id, completions, rnk`

- `rnk` starts at 1 per country; ties in `completions` are broken by `title_id` ascending (so `rnk` has no ties).
- Titles with zero completed plays in the window are not returned.
- Order the result by `country`, then `rnk`.

Use window functions. The interviewer runs the string on SQLite with your parameters; write your own checks on a small
table first (what edge cases will you insert?).
