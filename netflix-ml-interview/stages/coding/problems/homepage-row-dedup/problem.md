---
variant: practical
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Homepage row deduplication
minutes: 35
---
# Homepage row deduplication

The homepage is a list of rows; each row is a list of title ids in display order. Candidate generators often return the
same title in several rows, which makes the page feel repetitive.

Write `dedup_rows(rows, n)` that returns a new list of rows after deduplication:

- Rows are processed top to bottom, items left to right.
- Inside one row a title may appear at most once (the first occurrence is kept).
- The first `n` **kept** positions of every row are the "visible" positions. A title that already occupies a visible
  position in this row or in an earlier row cannot take another visible position: it is dropped from the row.
- After the first `n` kept positions, only the within-row rule applies. A title shown off-screen in an earlier row may
  appear in a visible position of a later row (it was never visible).
- Dropped items are removed, so later items shift left (and may become visible).
- Do not mutate the input. `n >= 0`. Keep the relative order of kept items.

Example with `n = 2`:

```
rows = [["a", "b", "c", "a"],
        ["b", "d", "e", "c"],
        ["c", "f", "g"]]
-> [["a", "b", "c"],        # second "a" dropped (within-row)
    ["d", "e", "c"],         # "b" is visible in row 0 -> dropped; d, e take the visible slots; c is off-screen
    ["c", "f", "g"]]         # c was only off-screen above, so it may be visible here
```

Write your own tests before or while you implement. The interviewer will run a hidden suite afterwards.
