# Interviewer notes (private - never show to the candidate)

Repo: feature_service (TTL + LRU cache in front of a feature backend). Two flaws; see flaws.yaml.

## What good looks like
- Decomposition: Part 1 split into (a) partition ids into hits/misses (dedupe preserving order), (b) one
  fetch_many, (c) cache fill, (d) counters. Part 2 as a small signature change: `cache.put(..., ttl=)` already
  supports per-entry TTL, so no cache redesign is needed.
- Prompting: gives the AI the contract (one backend call, duplicates, unknown ids omitted, key includes
  feature set), points it at the right files, asks for a small diff plus tests.
- Verification: reads the diff before `::apply`; runs the tests; writes tests that exercise the contract
  (two feature sets with the same entity id; a clock advanced to the exact TTL boundary; duplicates; all-hit batch makes zero backend calls).
- Pushback: spots that the key drops the feature set (flaw key-collision) or that expiry now uses `>`
  (flaw ttl-boundary) by reading or by a targeted test, and tells the AI pair to fix it with a reason.

## Flaw timing
- key-collision appears on a get_many prompt. A candidate who specifies "key must include feature set" in
  the prompt may not trigger it; record that as strong prompting, not as a missed flaw.
- ttl-boundary appears on a ttl/expiry prompt. The existing test suite will NOT catch it; only a boundary test will.

## Probes if the candidate is quiet
- "What would convince you this is safe to ship on the ranking request path?"
- "What does the AI's diff assume about keys?" / "What is the exact moment an entry stops being valid?"
- Extension: how would you add negative caching for unknown ids, or a stampede guard for concurrent misses?

## Signals for the evaluator
- Applying a diff without reading it, or declaring done on green tests alone, is a verification gap.
- Rewriting everything by hand and ignoring the AI is a weak ai_direction signal (tool is part of the job).
- Reasonable depth: unit tests plus one boundary/collision test. Stampede or negative caching are extension, not required.
