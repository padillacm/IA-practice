# Spec Delta

## Purpose

Stores each simulated interview session only on the local machine, outside version control, and summarizes the candidate's evolution across sessions in a comparable way.

## ADDED Requirements

### Requirement: Local record of each session
The system SHALL store each session in its own directory inside the local sessions directory, identified by date and a short id. It will contain:
- the configuration and the state of each instance;
- one transcript and one scorecard per instance;
- the materials (code, take-homes);
- the cut and debrief decisions, if any.

#### Scenario: Completed session
- **WHEN** a session of two instances with a debrief ends
- **THEN** its directory contains the configuration, two transcripts, two scorecards and the decision

### Requirement: Sessions outside the repository
The sessions directory SHALL be in `.gitignore`. The system SHALL NOT stage, commit or push session files, nor offer to do so. Before writing, it SHALL check that the directory is ignored and that none of its files is tracked; if this does not hold, it will not write.

#### Scenario: Ignored directory
- **WHEN** a session is created
- **THEN** `git status` shows no session file

#### Scenario: Missing ignore
- **WHEN** the sessions directory is not ignored or contains tracked files
- **THEN** the system does not write the session, warns and states how to fix it

#### Scenario: Outside a git repository
- **WHEN** the simulator runs outside a git repository
- **THEN** the system writes the session and warns that there is no version control to protect

### Requirement: Warning in ephemeral environments
If it detects that it is running in an ephemeral remote environment, the system SHALL warn at start that the local history is lost when the environment is recycled.

#### Scenario: Claude Code on the web
- **WHEN** the session starts in a remote Claude Code container
- **THEN** the configuration summary includes that warning

### Requirement: Incremental saving
The system SHALL persist each turn in the transcript and update the instance state, including active time, after each turn. This way an interruption does not lose the stage in progress and the interviewer can be rebuilt.

#### Scenario: Interrupted conversation
- **WHEN** the conversation is cut off in the middle of a stage
- **THEN** the transcript has all the turns up to the last one, and the instance stays "in progress" with its time consumed

### Requirement: Comparable progress summary
The system SHALL maintain, in the local directory, a progress summary that groups scores by stage, variant and competency id in chronological order, showing at each point the level and the rubric version. "No evidence" will not be represented as a low score, and practice stages will be marked as such.

#### Scenario: Repeat a stage
- **WHEN** the candidate completes `ml-system-design@design` for the second time
- **THEN** the summary shows the two scores for each competency in chronological order

#### Scenario: Different level or version
- **WHEN** the repetition is at another level or with another rubric version
- **THEN** the summary indicates it at those points and marks the break in comparability

#### Scenario: Check progress
- **WHEN** the candidate invokes `/netflix-ml-interview progress`
- **THEN** the system shows the summary without starting any session

### Requirement: History of used questions
The state of each session SHALL record the questions and problems used in each instance, so that the selection for future sessions can exclude them.

#### Scenario: Question record
- **WHEN** an instance ends
- **THEN** its state lists the ids of the questions or problem used
