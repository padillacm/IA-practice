# Task: merge season-suffixed series titles

You own `title_dedup`, which groups catalog records that describe the same title so downstream
ranking features are not split across duplicates. Code is in `workspace/`; run `python -m unittest`
from that directory.

You may use the AI pair (`::ai <prompt>`). It proposes diffs; nothing is applied until `::apply`.
You are responsible for what you apply.

## The change

Ingestion now sends series titles with season markers, so the same series appears several times:
`"Stranger Things"`, `"Stranger Things: Season 4"`, `"Stranger Things (Season 4)"`, `"Stranger Things - Limited Series"`.

Make `normalize_title` ignore a trailing season or limited-series marker for records of kind `series`
so these group together. Requirements:
- Only trailing markers are removed: `Season <number>`, `Limited Series`, optionally introduced by `:` or `-`, or wrapped in parentheses.
- Movies must be unaffected (a movie called "Season of the Witch" must not change).
- Regional qualifiers such as `(US)` / `(UK)` must keep series apart.
- Keep existing tests passing and add tests for the new behavior.

Hint: `canonical_key` has access to the record kind; `normalize_title` currently does not.

## Expectations

- Be ready to explain how you know the change is correct and what you chose not to handle.
