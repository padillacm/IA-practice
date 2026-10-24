---
variant: lc-style
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Longest substring without repeated characters
minutes: 25
---
# Longest substring without repeated characters

Implement `longest_unique_substring(s)` returning the **length** of the longest substring of `s` that has no repeated
character. Strings may contain any Unicode characters (including the empty string).

Then implement `longest_unique_span(s)` returning `(start, length)` of the first such longest substring (smallest
start). For the empty string return `(0, 0)`.

Target O(n) time. State the complexity and the invariant of your loop. Write your own tests first or alongside.
