---
stage: coding
rubric_version: 1
---

# Rubric: coding

L5 is the anchor level; L4 and L6 bars are extrapolated from it. Netflix publishes no common scale, and the thresholds below are
pedagogical. Evidence comes from the transcript, the hidden-suite result and the candidate's own tests.

## Shared definitions
- **Yes**: the observable behavior in the level's row of the competency table occurs without a hint, backed by a
  transcript quote or a test result.
- **No**: the behavior occurs only after one or more hints, or occurs partially (for example, a correct solution that is
  slower than the expected complexity and is not improved when asked).
- **Strong No**: the main problem is not solved correctly by the end, the candidate writes no tests even when asked, or the
  candidate blames the tooling or the interviewer for a defect they introduced.
- **Strong Yes**: meets the Yes bar of the next level up, with evidence (for example, an L5 candidate who designs a thread-safe
  interface and tests the invariant).
- No evidence: a block never took place for a reason outside the candidate's control (for example, no time for part 2).

## problem_solving
core: true

| Level | Yes bar |
|---|---|
| L4 | Asks at least one clarifying question about inputs or ties, writes a working brute-force or direct solution for the main problem, and traces it by hand on the statement example. |
| L5 | Asks clarifying questions that resolve every ambiguity in the statement before coding, states the brute-force baseline and its cost, and reaches the intended data structure or technique without a hint. |
| L6 | Resolves the ambiguities, reaches the intended technique within the first third of the session, and states the invariant that makes it correct and the input that would break a naive version. |

## code_quality_correctness
core: true

| Level | Yes bar |
|---|---|
| L4 | The solution passes the statement example and at least 80% of the hidden suite; names are descriptive; the input is not mutated. |
| L5 | The solution passes the full hidden suite on the first or second run, splits logic into small functions, and handles empty input, ties and boundary values explicitly. |
| L6 | The solution passes the full hidden suite on the first run and exposes an interface that supports the follow-up (updates, a second consumer or per-row configuration) without a rewrite. |

## testing_verification
core: true

| Level | Yes bar |
|---|---|
| L4 | Writes at least three tests when asked, including one empty or boundary case, and runs them. |
| L5 | Writes tests unprompted before declaring done, covers boundaries (empty, ties, k=0 or equivalent) plus a randomized comparison against a brute-force oracle, and fixes a failing case by reading the failure. |
| L6 | Writes tests unprompted that state the invariant under test, adds an oracle-based property test and a performance or scale test, and says which class of defect the suite still cannot catch. |

## complexity_optimality
core: false

| Level | Yes bar |
|---|---|
| L4 | States the time complexity of the final solution when asked and identifies the dominant loop or operation. |
| L5 | States time and space complexity unprompted, reaches the expected complexity for the problem (for example O(n) for the window, O(log n) per update), and names one remaining inefficiency. |
| L6 | Reaches the expected complexity, compares at least two alternative structures with their constants and failure inputs, and picks one with a stated reason tied to the workload. |

## production_followups
core: false

| Level | Yes bar |
|---|---|
| L4 | Names at least one production concern (data volume or thread safety) for the extension question when prompted. |
| L5 | Raises scale or concurrency unprompted and gives a concrete design step: a partition key, a lock or snapshot strategy, or an offline versus online split. |
| L6 | Gives a design with partition key, skew handling, failure and retry behavior, and the metric or alert that would show it is degraded, and states a trade-off they accept. |

## culture_signals
core: false
memo_values: [candor, judgment, curiosity, resilience]

| Level | Yes bar |
|---|---|
| L4 | Says plainly what they do not know or what they got wrong, without defensiveness, at least once during the session. |
| L5 | Disagrees with the interviewer's worse proposal with a technical reason, proposes a measurement to settle it, and accepts the interviewer's point when it holds. |
| L6 | Names the weakest part of their own solution before being asked, states what they would verify before shipping, and asks a question that reveals how the team makes engineering decisions. |
