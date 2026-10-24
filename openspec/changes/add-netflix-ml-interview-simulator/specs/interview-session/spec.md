# Spec Delta

## Purpose

Lets the candidate configure and run a simulated Netflix interview session for ML roles, choosing role, level, language and which stages to practice, and orchestrates the transition between stages and phases.

## ADDED Requirements

### Requirement: Session start with explicit configuration
The system SHALL start each session with these values, requested from the candidate or received as arguments: role (`mle`, `rs`, `ds`), level (L4, L5 or L6; L5 by default), language, stages, team domain, feedback mode (immediate or deferred), `time_scale` and, optionally, a candidate background file. It SHALL NOT begin any stage until the candidate confirms the summary.

#### Scenario: Interactive configuration
- **WHEN** the candidate invokes `/netflix-ml-interview` without arguments
- **THEN** the system asks for the missing values, proposes the defaults, shows the summary and waits for confirmation

#### Scenario: Configuration by arguments
- **WHEN** the candidate invokes `/netflix-ml-interview role=mle stages=ml-system-design`
- **THEN** the system uses the defaults for the rest (L5, English, recsys domain, immediate feedback, `time_scale` 1.5), shows the summary and asks for confirmation

#### Scenario: Invalid value
- **WHEN** the candidate specifies a stage, variant, role, level, domain or language that does not exist, or a variant incompatible with the role (e.g. `coding@foo`)
- **THEN** the system rejects the value, lists the valid options and does not start the session

### Requirement: Roles and their equivalence
The `rs` role SHALL cover Research Scientist, ML Scientist and Applied Scientist, and `ds` SHALL be "Data Scientist (experimentation & analytics)". The summary SHALL state which role each title corresponds to.

#### Scenario: Applied Scientist
- **WHEN** the candidate says their position is "Applied Scientist"
- **THEN** the system proposes the `rs` role and explains that `ds` is the experimentation and analytics track

### Requirement: Candidate background
If the candidate provides a background file (CV or projects), the system SHALL extract a candidate profile from it and give it to all interviewers. If they do not provide one, the profile SHALL be built from what they say in `hm-screen`, when that stage is done.

#### Scenario: No background and no hm-screen
- **WHEN** the candidate does only `project-deep-dive` without providing a background
- **THEN** the interviewer starts by asking them to summarize the project they want to discuss

### Requirement: Single session language
The default language SHALL be English throughout the session: configuration, interview, scorecards, debrief and study plan. With `lang=es`, all of these SHALL be in Spanish. Standard technical terms and file enums stay in English in both modes.

#### Scenario: English by default
- **WHEN** the candidate does not specify a language
- **THEN** the interview, the scorecard and the debrief are in English

#### Scenario: Everything in Spanish
- **WHEN** the candidate starts with `lang=es`
- **THEN** the configuration, the interview, the scorecards, the debrief and the study plan are in Spanish

### Requirement: Default loop by role
The catalog SHALL define for each role a default loop in three phases (screen, VO1, VO2), with the variant of each entry, and SHALL state whether the role has a cut between VO1 and VO2. The system will use it when the "full loop" is requested and will report before starting the stages of each phase and the optional ones.

#### Scenario: Full ML Engineer loop
- **WHEN** the role is `mle` and the full loop is requested
- **THEN** the summary shows:
  - screens: `recruiter-screen`, `hm-screen` and `technical-screen@ml-coding`;
  - VO1: `coding@practical`, `ml-system-design@design` and `culture`;
  - VO2: `ml-depth`, `project-deep-dive`, `partnership` and `hm-onsite`;
  - the cut enabled.

#### Scenario: Full Research Scientist loop
- **WHEN** the role is `rs` and the full loop is requested
- **THEN** VO1 includes `presentation@research-talk` and `ml-system-design@problem-framing`, and the cut appears disabled

#### Scenario: Full Data Scientist loop
- **WHEN** the role is `ds` and the full loop is requested
- **THEN** the screens include `technical-screen@sql` and `technical-screen@stats`, VO1 includes `experimentation@design-case` and `experimentation@analysis-case`, and the default domain is experimentation

### Requirement: Stage instances
Each execution of a stage in a session SHALL have a unique instance id (`NN-<stage>@<variant>`) that identifies its agent, its transcript, its scorecard and its state. This way the same stage can appear several times in a session.

#### Scenario: Two technical screens
- **WHEN** a `ds` session runs `technical-screen@sql` and `technical-screen@stats`
- **THEN** each has its own transcript and its own scorecard, with no collisions

### Requirement: Selection of stages to simulate
The system SHALL allow simulating the default loop, a single phase (`stages=vo1`), a single stage or any subset, with specific variants (`stage@variant`) and optional stages. A stage without an explicit variant SHALL use the role's default variant. The order SHALL be the canonical one (phase and then catalog), unless the candidate asks for another.

#### Scenario: A single stage
- **WHEN** the candidate chooses only `experimentation`
- **THEN** the system runs that stage, issues its scorecard and does not convene the debrief

#### Scenario: Optional stage for the role
- **WHEN** an `mle` chooses `ml-fundamentals`
- **THEN** the system uses the `breadth` variant

#### Scenario: One phase
- **WHEN** the candidate chooses `stages=vo1` with role `mle`
- **THEN** the system runs `coding@practical`, `ml-system-design@design` and `culture`, in that order

### Requirement: List the catalog
The system SHALL show the catalog with `/netflix-ml-interview stages`, without starting any session.

#### Scenario: Listing
- **WHEN** the candidate invokes `/netflix-ml-interview stages`
- **THEN** the system lists the stages by phase, with duration, variants and which default loops they appear in

### Requirement: Transition and cut between phases
When a stage ends, the system SHALL save its transcript, obtain its scorecard according to the feedback mode and offer to continue, pause or finish. If the role has an active cut and the session includes VO1 and VO2, when VO1 ends it SHALL convene the cut debrief. If the cut is negative, it SHALL offer to finish or continue in practice mode.

#### Scenario: Negative cut
- **WHEN** the cut debrief decides not to continue
- **THEN** the system shows the decision and asks whether to finish or continue with VO2 in practice mode, and records it in the session

#### Scenario: Finish early
- **WHEN** the candidate decides to finish with pending stages
- **THEN** the system marks those stages as not done and, if two or more are completed, convenes the debrief stating that the loop is incomplete

### Requirement: Pause and resume
The system SHALL allow pausing and resuming in another conversation as long as the local files exist. If the instance was in progress, it SHALL rebuild the interviewer from the transcript, with the same persona and without introducing itself again. If there are several pending sessions, it SHALL list them to choose from.

#### Scenario: Resume an in-progress stage
- **WHEN** the candidate invokes `/netflix-ml-interview resume` and the last instance was left in progress
- **THEN** an interviewer rebuilt from the transcript and the remaining time responds to the candidate's last message

#### Scenario: Nothing to resume
- **WHEN** the candidate asks to resume and there are no pending local sessions
- **THEN** the system says so and offers to start a new session

### Requirement: Candidate commands during the session
During a stage, the system SHALL recognize commands prefixed with `::` as instructions to the orchestrator and not as answers to the interviewer: `::time`, `::pause`, `::end`, `::ai <prompt>`, `::apply` and `::help`. The `::` prefix avoids the conflict with CLI slash commands.

#### Scenario: Check time
- **WHEN** the candidate types `::time` in the middle of a stage
- **THEN** the system shows the elapsed time and the budget, and the interviewer does not receive it as an answer

#### Scenario: Pause
- **WHEN** the candidate types `::pause`
- **THEN** the stage clock stops, the state is saved and the system states how to resume

#### Scenario: Unknown command
- **WHEN** the candidate types `::foo`
- **THEN** the system shows `::help` and sends nothing to the interviewer

### Requirement: Degraded mode
If the channel for sending messages to a subagent is not available, the system SHALL warn and conduct the stage in the main thread with the interviewer's persona. The evaluation SHALL still be done by a separate agent, and the degraded mode SHALL be recorded.

#### Scenario: No message channel
- **WHEN** the interviewer cannot be resumed through messages
- **THEN** the system warns, continues in degraded mode and the session is marked as degraded
