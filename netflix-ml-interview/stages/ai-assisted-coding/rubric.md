---
stage: ai-assisted-coding
rubric_version: 1
---
# AI-assisted coding - rubric

Scoring is relative to the Yes bar of the candidate's level (L5 is the anchor; L4 and L6 are extrapolated).
Evidence comes from the candidate's own turns, their prompts to the AI pair, the diffs they applied or rejected, and the
test results reported by the orchestrator. Planted flaws matter only for what the candidate did when one was triggered.

- **Strong No (SN)**: applies AI diffs without reading them and states or implies correctness with no check, OR hides or
  misrepresents what the AI produced, OR ships a change that breaks previously green tests without noticing. One such
  instance on a core competency is enough.
- **No (N)**: part of the Yes bar is observed but a required behavior is missing (for example reads diffs but never runs or adds a
  test; prompts without constraints and never iterates; no plan before building).
- **Yes (Y)**: every behavior in the level's Yes bar is observed at least once in the candidate's turns.
- **Strong Yes (SY)**: the Yes bar plus unprompted behavior one level up (for example a boundary test that exposes a flaw
  the existing tests miss, an explicit contract given to the AI before it errs, or a clear account of what was left out and why).

Rules of thumb:
- A repo with no triggered flaw cannot lower `challenging_ai_errors`; score it `no_evidence` unless the candidate challenged
  something real. Inventing a defect in a correct diff and insisting on it, after being asked for a failing input, counts against `verification_of_ai_output` and `culture_signals`.
- A candidate who states the exact contract in the prompt and so never triggers a flaw earns credit under `ai_direction`.
- A hint that moves the candidate forward caps the affected competency (nudge at Y, substantive hint at N).

## task_decomposition
core: true

| Level | Yes bar |
|---|---|
| L4 | Before the first `::ai` prompt, names at least two ordered steps for the task and asks the AI about one step at a time; the first prompt covers a single step. |
| L5 | Before the first `::ai` prompt, reads the relevant files, states a plan of three or more ordered steps with the interfaces each step touches, and sequences them so each step can be tested on its own; revises the plan aloud when the code contradicts it. |
| L6 | As L5, and also identifies which parts of the task to hand to the AI and which to write or review by hand, with a stated reason; names a risk to check early and orders the plan around it. |

## ai_direction
core: true

| Level | Yes bar |
|---|---|
| L4 | Prompts name the file or function to change and the desired behavior; when the diff misses part of the request, re-prompts with the missing part instead of hand-fixing silently. |
| L5 | Prompts include the contract (inputs, outputs, edge cases such as duplicates or boundaries) and what must not change; asks for a small diff plus tests; iterates at least once with a specific correction that cites the diff. |
| L6 | As L5, and also supplies constraints from the system context (request path latency, data semantics, at-least-once logging) in the prompt, and recovers a stalled or off-track AI exchange by resetting the context or splitting the request. |

## verification_of_ai_output
core: true

| Level | Yes bar |
|---|---|
| L4 | Reads each diff before `::apply` (says what it changes), runs the test suite after applying, and reports the result honestly. |
| L5 | Reads each diff before `::apply` and states what it assumes; writes at least one new test of their own for a boundary or interaction the existing tests do not cover; answers "how do you know it is correct" with a specific run or test, not "the tests pass". |
| L6 | As L5, and also designs checks for non-obvious failure modes of the domain (key collisions, exact time boundaries, leakage past a cutoff, wrongly merged records), and states what remains unverified and what it would take to verify it. |

## challenging_ai_errors
core: false

| Level | Yes bar |
|---|---|
| L4 | When a diff is shown to be wrong or unwanted (by a failing test or the candidate's own reading), rejects or corrects it instead of applying it, and says what was wrong. |
| L5 | Identifies a flawed assumption in a diff before applying it, or finds it with a targeted test of their own, explains the consequence in the system (not just "it is wrong"), and instructs the AI with a specific fix. |
| L6 | As L5, and also generalizes: states which other places in the code share the same assumption and checks them, and asks the AI for the reasoning behind a questionable proposal rather than only for another diff. |

## outcome_quality
core: true

| Level | Yes bar |
|---|---|
| L4 | At the end the original tests plus the candidate's new tests run green, and the required Part 1 behavior works on the task examples. |
| L5 | All parts of the task work; new behavior has tests including at least one edge case; default behavior is unchanged; the candidate can state what they chose not to handle. |
| L6 | As L5, and also changes stay small and consistent with the existing style, and the candidate proposes and sketches a concrete extension (for example stampede protection, confidence intervals, fuzzy matching with review) with its main risk. |

## culture_signals
core: false
memo_values: [candor, judgment, courage, curiosity]

| Level | Yes bar |
|---|---|
| L4 | Says out loud when something is unclear or when they are unsure about an AI proposal, and asks the interviewer or the code instead of guessing. |
| L5 | Owns what they applied: states a mistake or a skipped check without being asked, and rejects an AI proposal with a reason even when it looks plausible. |
| L6 | As L5, and also gives direct, respectful advice on how a team should use AI diffs (what must be read, what must be tested) and defends a position when challenged, changing it only on new evidence. |
