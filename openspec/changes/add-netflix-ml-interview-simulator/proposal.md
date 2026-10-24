# Proposal

## Why

Preparing for a Machine Learning interview loop at Netflix requires practicing very different stages: screens, practical coding, fundamentals, ML system design, experimentation, presentations, deep dive and culture. Today there is no way to rehearse them with realistic interviewers, an independent evaluation and a record of progress. The repo already has the `recsys-course/` course ("from zero to Netflix level") and the multi-agent `course-builder` flow. A simulator in Claude Code, aligned with what is publicly known about the process (see `research.md`), closes the loop: study, practice, receive feedback and go back to studying.

## What Changes

- **New Claude Code skill `/netflix-ml-interview`** that orchestrates a simulated interview session.
  - The candidate chooses role, level, language, team domain and **which stages to simulate**: the default loop for their role, a phase, a single stage or any selection.
  - Roles: ML Engineer; Research / ML / Applied Scientist; Data Scientist (experimentation & analytics).
  - Levels: L4–L6, with L5 as the default.
  - Optionally, the candidate can provide their CV or background.
- **Language**: everything in English by default (interview, scorecards and final decision). `lang=es` switches **everything to Spanish**.
- **Catalog of 14 stages in three phases**, based on the research:
  - **Screens**: recruiter, HM and technical screen (with per-role variants, including the review of a production PR).
  - **VO1** (general): presentation, coding, AI-assisted coding, ML fundamentals, ML system design, experimentation and culture ("Dream Team" with a director).
  - **VO2** (team): ML depth, project deep dive, partnership and HM onsite.
  - Each role has its default loop. The cut between VO1 and VO2 is active for MLE and optional for the other roles.
- **17 subagents**, all without Bash or write access:
  - One interviewer per stage, with persona, style, question bank, follow-ups and time budget, giving no feedback during the stage.
  - An evaluator that scores blind, with verified quotes and explicit pedagogical rules.
  - A hiring manager debrief. Netflix has no hiring committee, so the debrief simulates the panel discussion (pass / fail, seeking consensus) and the HM's decision as "informed captain": Hire with level, No Hire, or "not a fit for this team, referred".
  - An "AI pair" assistant for the AI-assisted coding round.
- **`sim.py` helper (stdlib)**: does everything deterministic. That includes the git guard, session state, active time, question selection, test execution, quote verification, interviewer rebuilding and progress.
- **Local-only sessions**: they are stored in a git-ignored directory, and the system never adds or commits them.
- **Versioned knowledge base** (`netflix-ml-interview/`) with catalog, banks, rubrics, sources and an evaluation gold set, separate from the prompts.

## Capabilities

### New Capabilities
- `interview-session`: session configuration and orchestration (role, level, language, domain, background, stage and phase selection), stage instances, cut between phases, `::` commands, pause, resume and degraded mode.
- `interview-stages`: catalog of stages and variants, and observable interviewer behavior (persona, style, turn contract, pacing, time, executable coding, AI-assisted coding, culture).
- `interview-evaluation`: versioned rubrics, independent evaluation with verifiable evidence, pedagogical recommendation rule, per-role weights, cut, debrief, study plan and evaluator quality.
- `interview-history`: local session record outside git, incremental saving and comparable progress.

### Modified Capabilities
<!-- None: the repo has no previous specs. -->

## Impact

- **New files**:
  - `.claude/skills/netflix-ml-interview/` (skill and handoff protocol);
  - `.claude/agents/netflix-*.md` (17 agents);
  - `netflix-ml-interview/` (knowledge base, `sim.py` and validator);
  - root `.gitignore` with `netflix-ml-interview/sessions/`;
  - `.claude/settings.json` with a permission for `sim.py`.
- **Dependencies**: none at runtime, apart from Claude Code and Python 3 (stdlib). The content of some coding problems uses numpy and pandas (`requirements.txt`). CI installs them and the validator skips them with a warning if they are missing.
- **CI**: a workflow in `.github/workflows/` that runs the validator and the `sim.py` tests. Conversational behavior is verified by hand, with the gold set and smoke tests.
- **Existing content**: `recsys-course/` is only read, to link the study plan.
- **Limitations**:
  - It is a simulation based on public information, and much of the evidence comes from SWE loops. Real loops vary by team, the L4 and L6 descriptors are extrapolated and there is no affiliation with Netflix.
  - In ephemeral environments (Claude Code on the web), local sessions are lost when the container is recycled.
