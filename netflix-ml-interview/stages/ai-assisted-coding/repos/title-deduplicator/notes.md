# Interviewer notes (private - never show to the candidate)

Repo: title_dedup. ZERO flaws. The AI pair is expected to return a correct, reasonably minimal diff.
This repo tests whether the candidate verifies proportionately and does NOT invent problems or reject good output.

## What a correct solution looks like
- Pass the kind into normalization (e.g. `normalize_title(title, kind=None)` or strip in `canonical_key` for series only), with a regex anchored at the end of the string, applied BEFORE punctuation is removed or equivalently on the cleaned words.
- Handles `: Season 4`, `(Season 4)`, `- Limited Series`, case-insensitively; leaves "Season of the Witch" (movie) and mid-title "Season" untouched; leaves `(US)`/`(UK)` intact.
- Existing tests remain green; new tests cover each marker form, the movie case and regional qualifiers.

## Observation guidance
- Strong: reads the diff, runs tests, adds 2-3 targeted tests (movie unaffected, regional qualifier, marker only at the end), then applies and moves on, stating what was deliberately left out (e.g. "Part 2", "Volume 1", non-English markers).
- Weak (over-skepticism): rejecting a correct diff for speculative reasons, demanding rewrites to taste, or claiming a bug that does not exist (e.g. insisting that dropping the leading article is a defect, or that `(US)` should be stripped).
- Weak (under-verification): applies without reading, or claims done without running tests.
- If the candidate claims a bug, ask them to show a failing input. A sound candidate produces one or retracts; record the retraction as positive candor/judgment.
- Extension discussion (not required): fuzzy matching (edit distance / token sets) with blocking, transitive merges, precision/recall evaluation on a labeled sample, human review queue for low-confidence merges.

## Reminder
flaws_triggered should be empty for this repo. If the AI pair does return a mistake, note it in the summary as an unplanned error and score the candidate on how they handled it.
