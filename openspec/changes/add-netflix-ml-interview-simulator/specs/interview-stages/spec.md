# Spec Delta

## Purpose

Defines the catalog of stages of the Netflix ML interview process and the observable behavior of the simulated interviewers in each one, aligned with the public information collected in `research.md`.

## ADDED Requirements

### Requirement: Stage catalog
The system SHALL offer 14 stages: `recruiter-screen`, `hm-screen`, `technical-screen`, `presentation`, `coding`, `ai-assisted-coding`, `ml-fundamentals`, `ml-system-design`, `experimentation`, `culture`, `ml-depth`, `project-deep-dive`, `partnership` and `hm-onsite`. For each one it SHALL declare default phase, duration, variants with their per-role default, competencies, persona and style.

#### Scenario: Catalog validation
- **WHEN** the simulator validation is run
- **THEN** the 14 stages have all their fields, and each loop entry points to an existing stage and variant compatible with the role

### Requirement: Sources and variability notice
Each stage SHALL document the public sources it is based on, with their confidence level, and mark as assumptions the durations and the extrapolated level descriptors. When starting a session, the system SHALL warn that real loops vary by team and level.

#### Scenario: Notice at start
- **WHEN** the configuration summary is shown
- **THEN** it includes a line stating that the simulated loop is an approximation and that the real structure must be confirmed with the recruiter

### Requirement: Technical-screen variants
`technical-screen` SHALL offer:
- `ml-coding` (MLE): about 20' of ML questions and about 40' of practical coding of medium difficulty.
- `ml-framing-coding` (RS).
- `sql` and `stats` (DS).
- Optional: `fundamentals-pr-review`, `intern-project-coding` (20' of project + 40' of coding, format reported for internships) and `oa`.

#### Scenario: PR review
- **WHEN** an `mle` does `technical-screen@fundamentals-pr-review`
- **THEN** after the fundamentals (e.g. attention with Q/K/V or KV cache), the interviewer shows a PR whose tests pass and asks what would fail in production; then discusses how to serve those features with different latencies

#### Scenario: DS stats
- **WHEN** a `ds` does `technical-screen@stats`
- **THEN** the stage covers regression interpretation, type I/II errors, multiple testing and FDR, CLT and t-stat, bootstrap, power and MDE and, optionally, causal inference (ATE, IV/LATE)

### Requirement: Onsite stage variants
The onsite stages SHALL have these variants:
- `presentation`: `research-talk` (RS, 45') and `take-home` (DS).
- `coding`: `practical` (MLE), `ml-coding` (RS), `sql-pandas` (DS) and `lc-style` (optional).
- `ml-fundamentals`: `breadth` and `modeling-case` (DS, optional, no direct evidence).
- `ml-system-design`: `design` (MLE) and `problem-framing` (RS).
- `experimentation`: `design-case` and `analysis-case`.

#### Scenario: DS experimentation
- **WHEN** a `ds` does the full loop
- **THEN** VO1 includes an experiment design case and a results analysis case (quantiles, heterogeneous effects, covariate adjustment)

### Requirement: Prior materials for presentation
For `presentation`, the system SHALL deliver the assignment before the stage: a take-home with a synthetic dataset (DS) or the prompt for a research talk about the candidate's own work (RS). The session SHALL stay paused until the candidate says they are ready.

#### Scenario: Take-home
- **WHEN** a `ds` reaches `presentation`
- **THEN** the system generates the statement and the dataset in the session's local space, pauses and, on resuming, the panel listens to the presentation and then asks questions

### Requirement: Two-part coding
In `coding`, the interviewer SHALL pose a practical problem and ask the candidate to write their own tests. If time remains, it SHALL extend it with at least one production follow-up: scale, storage or concurrency. The optimality of the solution SHALL be recorded.

#### Scenario: Production follow-up
- **WHEN** the candidate solves the main problem with time to spare
- **THEN** the interviewer asks how it would work with multiple threads or at production scale

### Requirement: Executable coding
In `coding`, in `ai-assisted-coding` and in the coding part of `technical-screen`, the system SHALL accept the solution pasted in the chat or written to a file in the session's local space. If it is in a file, the orchestrator (not the interviewer) SHALL run the problem's tests and the candidate's tests, in plain view of the candidate, and pass the result to the interviewer.

#### Scenario: Solution in a file
- **WHEN** the candidate writes their solution in the indicated file and says "done"
- **THEN** the tests are run, the result is recorded in the transcript and the interviewer asks about complexity, edge cases and optimality

### Requirement: AI-assisted coding round
`ai-assisted-coding` SHALL give the candidate a small codebase and an AI assistant invocable with `::ai <prompt>`. The assistant returns proposals without applying them, and `::apply` applies them. By design, it can make between 0 and 2 plausible mistakes per repo. The following are evaluated: work decomposition, instructions, verification, the ability to push back on the mistakes and the result.

#### Scenario: Assistant mistake
- **WHEN** the assistant proposes a change that passes the existing tests but introduces a subtle bug
- **THEN** the transcript records whether the candidate detected it, and the interviewer asks about their verification strategy without revealing the bug

### Requirement: One independent interviewer per stage
Each instance SHALL be conducted by its own agent, with its own context, which does not know the transcripts of other stages. All receive the same candidate profile (background or `hm-screen`), and each deep-dive interviewer focuses on a different part of that profile.

#### Scenario: Isolation between stages
- **WHEN** the candidate moves from `coding` to `ml-fundamentals`
- **THEN** the new interviewer introduces themselves as a new person and makes no reference to what happened in `coding`

### Requirement: Realistic loop personas
Each stage SHALL have the persona that fills that role at Netflix:
- recruiter;
- HM: cordial and selling Netflix in `hm-screen`, demanding in `hm-onsite`;
- senior engineer or scientist;
- panel of two in `presentation`;
- manager or director of a partner team in `partnership`;
- director in `culture` ("Dream Team").

Directors SHALL reserve time for the candidate's questions.

#### Scenario: Director in culture
- **WHEN** `culture` begins
- **THEN** the interviewer introduces themselves as a director, asks intense questions about scale, accountability and risk, and reserves time for the candidate's questions

### Requirement: Variable interviewer styles
Each persona SHALL have a declared style (conversational, concise or incisive), because at Netflix interviews are not standardized. The style changes the tone, not the rigor.

#### Scenario: Concise style
- **WHEN** the `ml-depth` persona has a concise style
- **THEN** it asks short questions and direct follow-ups, with the same topics and the same time budget

### Requirement: Interviewer turn contract
Each interviewer turn SHALL end with exactly one block visible to the candidate and one block of factual metadata, with nothing after. The interviewer SHALL NOT write or assume candidate answers, nor use tools after its first turn.

#### Scenario: Malformed turn
- **WHEN** an interviewer response does not include both blocks
- **THEN** the orchestrator asks it to reformat once and, if it fails again, shows the raw text and flags it in the transcript

### Requirement: Pacing control by the interviewer
The interviewer SHALL politely interrupt and move to the next point once it has the signal for the current one. If the candidate dwells on parts that are not very relevant, it SHALL redirect them. Signal points left uncovered SHALL be recorded.

#### Scenario: Signal obtained
- **WHEN** in `ml-system-design` the candidate has already explained resource allocation well and keeps going deeper
- **THEN** the interviewer interrupts them and moves on to monitoring or crash handling

#### Scenario: Unfinished design
- **WHEN** the time in `ml-system-design` runs out without a complete design
- **THEN** the transcript records which signal points were left uncovered

### Requirement: Realism without live feedback
During a stage, the interviewer SHALL keep its persona and ask one question or follow-up per turn. It SHALL NOT reveal the rubric, scores, model answers or whether an answer is correct. It may give at most one hint per blockage, recorded with its level: nudge or substantive.

#### Scenario: Candidate asks for the answer
- **WHEN** the candidate asks "Is this right?" in the middle of `ml-fundamentals`
- **THEN** the interviewer asks them to reason it through or continue, without confirming or correcting

#### Scenario: Candidate stuck
- **WHEN** the candidate says they are blocked in `coding`
- **THEN** the interviewer gives at most one neutral hint and records it with its level and the affected competency

### Requirement: Questions adapted to role, level and domain
The orchestrator SHALL choose questions or problems from the bank compatible with the role, level, variant and domain. While alternatives remain, it will exclude those already used in previous local sessions. The banks SHALL be based on publicly reported topics and on practices published by Netflix, without asking for specific figures from those publications.

#### Scenario: Second time in coding
- **WHEN** the candidate repeats `coding` with the same role and level
- **THEN** the main problem is different from the previous time's

#### Scenario: Senior level
- **WHEN** the session is L6 in `ml-system-design`
- **THEN** the interviewer additionally demands trade-offs at scale, availability, safety, online validation and cross-team scope

#### Scenario: Follow-up question
- **WHEN** the candidate mentions "I'd use a two-tower model for retrieval"
- **THEN** the interviewer follows up on that point (negative sampling, cold start or serving) before changing topic

### Requirement: Time budget
Each stage SHALL have an active-time budget, scaled by `time_scale` and not counting pauses. At 80 % the interviewer SHALL give a warning, at 90 % move to the candidate's questions and at 100 % close the stage.

#### Scenario: Time exhausted
- **WHEN** the scaled active time reaches the budget
- **THEN** the interviewer closes the current topic and ends the stage

#### Scenario: Pause
- **WHEN** the candidate pauses for 10 minutes and then resumes
- **THEN** those 10 minutes do not count toward the budget

### Requirement: Culture based on the current memo
The `culture` stage SHALL evaluate 3–4 values per session from Netflix's current memo (selflessness, judgment, candor, creativity, courage, inclusion, curiosity, resilience) and its concepts: keeper test, context not control, informed captain, farming for dissent and disagree then commit. It will do so with behavioral questions that require concrete cases with measurable impact.

#### Scenario: Generic answer
- **WHEN** the candidate answers with generalities
- **THEN** the interviewer asks for a real case: what happened, what they did, the measurable result and what they would do differently

### Requirement: Culture signals in all stages
All interviewers SHALL record the culture signals they observe. When it fits the stage's topic, they SHOULD ask a follow-up that reveals them (e.g. how they would defend a trade-off to a stakeholder).

#### Scenario: Signal observed in system design
- **WHEN** the candidate spontaneously mentions that they asked for contrary opinions before deciding
- **THEN** the interviewer records it as a signal of the corresponding value

### Requirement: Keep the session language
The interviewer SHALL conduct the stage in the session language even if the candidate switches language. The switch SHALL be noted without penalty.

#### Scenario: Candidate language switch
- **WHEN** the language is English and the candidate answers once in Spanish
- **THEN** the interviewer continues in English and the switch is noted
