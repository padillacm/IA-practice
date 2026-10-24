---
variant: oa
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: OA coding 2 - format conversion and imputation
minutes: 35
---
# OA coding 2: format conversion and imputation

Event features arrive as a list of dict records (row-oriented, like JSON lines). Some keys are missing, and some values
are `None` or the empty string `""`: all three mean **missing**. Implement `to_columns(records)` returning a dict
`column -> list` (column-oriented) with these rules:

1. Columns are the union of all keys, in sorted order (the returned dict has its keys inserted in that order); every column
   list has `len(records)` entries, in record order.
2. A column is **numeric** if all of its non-missing values are `int` or `float` (not `bool`). Missing numeric values are
   imputed with the mean of the non-missing values (a float).
3. Any other column is **categorical**; missing values are imputed with the most frequent non-missing value (ties: the
   smallest value by string order).
4. A column with no non-missing value at all is dropped from the output.
5. Do not mutate the input. Return `{}` for empty input.

Also implement `impute_summary(records)` returning `{column: fill_value}` for the columns that needed at least one
imputation (use the same fill values as above).

This is an online assessment: no interviewer help. Write at least three tests of your own.
