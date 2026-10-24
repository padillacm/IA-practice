---
variant: lc-style
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Pairs of strings with no common characters
minutes: 30
---
# Pairs of strings with no common characters

Given a list `words` of lowercase ASCII strings (`a`-`z`; possibly empty, possibly repeated):

1. `count_disjoint_pairs(words)`: the number of index pairs `i < j` such that `words[i]` and `words[j]` share no
   character. An empty string shares nothing with anything.
2. `max_disjoint_product(words)`: the maximum of `len(words[i]) * len(words[j])` over disjoint pairs `i < j`, or 0 if
   none exists.

First write the straightforward version and state its complexity, then improve it. The expected improvement uses a
26-bit **bitmask** per word so that a disjointness check is a single AND. Discuss how many distinct masks there can be
and how that bounds the work.

Write your own tests, including a brute-force oracle.
