---
stage: technical-screen
rubric_version: 1
---

# Rubric: technical-screen

L5 is the anchor level; L4 and L6 bars are extrapolated from it. Netflix publishes no common scale, and the thresholds are pedagogical. Evidence comes from the
transcript, the hidden-suite or SQL execution results, and the answers to the variant's questions. The behaviors below
apply to every variant: read "the task" as the coding problem (`ml-coding`, `ml-framing-coding`, `intern-project-coding`, `oa`), the SQL
questions (`sql`), the statistics questions (`stats`) or the PR review (`fundamentals-pr-review`).

## Shared definitions
- **Yes**: the observable behavior in the level's row of the competency table occurs without a hint, backed by a transcript quote, a test result or an
  executed query result.
- **No**: the behavior occurs only after one or more hints, or occurs partially (for example, a correct SQL query that double counts users and is not
  corrected when asked about the count).
- **Strong No**: the main task is not solved correctly by the end, a central fact is stated wrongly and repeated after correction (for example,
  claiming a p-value is the probability that the null is true), or the candidate blames the tooling or the interviewer for their own defect.
- **Strong Yes**: meets the Yes bar of the next level up, with evidence (for example, an L5 candidate who finds the training/serving skew in the PR and
  proposes feature logging without a prompt).
- No evidence: a block never took place for a reason outside the candidate's control (for example, the interviewer ran out of time before the
  statistics questions on causal inference).
- Hints are recorded by step number (see `prs/*/issues.md`); each hint lowers the score for the competency it unblocks by at most one level.

## technical_knowledge
core: true

Evidence: ML fundamentals (regularization, boosting, embeddings, attention, KV cache), statistics (regression, error types, FDR, CLT, bootstrap, power,
IV), SQL semantics (window functions, joins, NULLs) and recsys basics, depending on the variant.

| Level | Yes bar |
|---|---|
| L4 | States the definition and the main mechanism correctly for each asked concept (for example, L1 yields sparse weights, a KV cache stores keys and values of past tokens) and gets the numeric answer right after one clarification. |
| L5 | Gives the mechanism and the reason for each concept, computes the numeric answers (t-statistic, MDE, BH rejections, posterior) with correct arithmetic, and names the assumption each result depends on without being asked. |
| L6 | Gives the reason and the failure case for each concept, connects it to a production consequence (for example, collinearity inflating standard errors, quadratic attention memory limiting context), and corrects a flawed premise in the interviewer's question. |

## coding_execution
core: true

Evidence: hidden-suite result, SQL executed on the dataset, code written live, the PR findings list.

| Level | Yes bar |
|---|---|
| L4 | The main solution (or the query for the first two SQL questions) passes the statement example and at least 80% of the hidden checks, and the candidate reads error output to fix a failure. |
| L5 | The solution passes the full hidden suite within the time (or the SQL returns the expected rows), uses the intended technique (window function, deque, rank-sum, anti-leak split), and handles empty input, ties and NULLs explicitly. In a PR review, identifies the leakage or non-idempotency and the unbounded join without a hint. |
| L6 | Passes the full hidden suite on the first run with an interface that extends to the follow-up, states the complexity and the scaling limit, and in a PR review identifies at least four findings across correctness, leakage, skew and scale with a fix for each. |

## problem_framing_communication
core: true

Evidence: how the candidate restates the task, asks questions, plans before coding and structures answers.

| Level | Yes bar |
|---|---|
| L4 | Restates the task, asks at least one clarifying question about inputs or definitions, and explains the solution in order when walking through it. |
| L5 | Resolves every ambiguity in the statement before coding, states the plan and the baseline cost before writing code, defines the metric or label and the unit of analysis in framing questions, and ranks issues by impact in a review. |
| L6 | Reframes the task around the decision it supports (for example, which launch decision an interleaving result informs), states assumptions and what would falsify them, and structures the answer so the conclusion comes first and the trade-offs second. |

## verification_testing
core: false

| Level | Yes bar |
|---|---|
| L4 | Runs the statement example and at least one additional case, or checks a SQL result by row count, before saying done. |
| L5 | Writes tests or checks unprompted, including an empty or NULL case and a comparison against a brute-force or manual calculation, and fixes a failure by reading its output. |
| L6 | Defines the invariant being tested, adds a randomized oracle check or a data-quality check (duplicates, orphan keys, sample ratio), and says which defect class the checks still miss. |

## culture_signals
core: false
memo_values: [candor, curiosity, judgment, resilience]

| Level | Yes bar |
|---|---|
| L4 | Says plainly when they do not know a concept or made a mistake, and continues without defensiveness. |
| L5 | Holds a correct position with a reason when the interviewer challenges it, changes it when shown evidence, and states what they would look up to settle a point they were unsure about. |
| L6 | Names the weakest part of their own answer before being asked, states what they would verify before acting on it, and asks about how the team validates its own models or experiments. |
