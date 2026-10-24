# Question bank: partnership

Behavioral prompts on cross-team collaboration, stakeholders and dependencies (research.md 2 Partnership). Original prompts, not recalled questions.

### partnership-collab-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - understands the partner's goals
  - agreed interface and ownership
  - outcome
```
Tell me about a project where your team depended on another team, or the reverse. What did each team need, and how did you agree on who does what?

Follow-ups:
- What did the other team want that you had not expected?
- How did you document the agreement?
- What went wrong?

### partnership-collab-02
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - builds shared context
  - early involvement
  - avoids surprises
```
Describe the last time you involved a partner team early in your work. What made you do it and what changed because of it?

Follow-ups:
- What did you hold back from sharing?
- How did you keep them informed afterwards?

### partnership-collab-ml-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: ml-platform
kind: main
signal_points:
  - platform users' needs
  - adoption
  - reliability vs speed trade-off
```
You maintain tooling that other model teams use. One team wants a feature that conflicts with another's. How do you handle it?

Follow-ups:
- Who decides?
- How do you tell the team that loses?

### partnership-collab-exp-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: experimentation
kind: main
signal_points:
  - partner trust in results
  - clarity of recommendation
  - shared metric definitions
```
A product team partner disagrees with the conclusion of your analysis. How do you work with them to reach a decision?

Follow-ups:
- What would make you change your conclusion?
- What if they decide to ship anyway?

### partnership-collab-rec-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: recsys
kind: main
signal_points:
  - downstream consumers of model output
  - interface and versioning
  - communication of changes
```
Your ranking model's output is consumed by three surfaces owned by other teams. You want to change its behavior. How do you roll that out with them?

Follow-ups:
- How do you find out who is affected?
- What if one team cannot adopt for a quarter?

### partnership-influence-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - evidence and framing for audience
  - outcome
  - own changed position
```
Tell me about a time you needed a stakeholder to change their mind and you had no authority over them. What did you do?

Follow-ups:
- What did you try that did not work?
- How did you know they were convinced?
- What did you change in your own view?

### partnership-influence-02
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - disagrees then commits
  - seeks dissent
  - decision recorded
```
Describe a decision that went against your recommendation. What did you do afterwards?

Follow-ups:
- How did you commit in practice?
- What did you ask for in return?
- Did you raise it again later, and how?

### partnership-influence-03
```yaml
roles: [mle, rs, ds]
levels: [L6]
variant: default
domain: any
kind: main
signal_points:
  - aligns leaders
  - makes trade-offs explicit
  - mechanism built
```
Two teams you do not manage have conflicting roadmaps, and both are important to the company. How have you handled that, and what did you leave behind so it would not recur?

Follow-ups:
- Who lost and how did you tell them?
- What did you escalate and when?

### partnership-dependency-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - noticed early
  - offered options
  - kept partner informed
```
Tell me about a dependency that slipped. When did you find out, whom did you tell, and what did you offer?

Follow-ups:
- What did you cut?
- What would you do earlier next time?

### partnership-dependency-02
```yaml
roles: [mle, rs, ds]
levels: [L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - competing priorities
  - visible trade-offs
  - escalation judgment
```
Describe a time your team's priorities conflicted with a partner's. How was it resolved, and who made the call?

Follow-ups:
- At what point did you escalate and why?
- Did your team lose? What happened?

### partnership-communication-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - structured message
  - states ask and deadline
  - adapts to audience
```
Pick a technical decision your team made and explain to me, as if I were a partner manager with five minutes, what changes for my team.

Follow-ups:
- What would you say to my director instead?
- What do you need from me and by when?

### partnership-feedback-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - receives feedback from partner
  - candor
  - action taken
```
What is the hardest thing a partner team has told you about how your team works, and what did you do with it?

Follow-ups:
- How did you respond in the moment?
- What changed?

### partnership-scenario-01
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: main
signal_points:
  - discovers impact early
  - communicates directly
  - negotiates scope
```
Scenario. My team consumes your team's output. You plan a change that would break our next quarter's launch. We have not talked yet. Walk me through what you do and say, starting today.

Follow-ups:
- What would you say if I say we cannot absorb it?
- What do you escalate and to whom?

### partnership-followup-theirgoal
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
signal_points:
  - empathy for partner goals
```
"What did the other team want, and what did you give up for it?"



### partnership-followup-escalate
```yaml
roles: [mle, rs, ds]
levels: [L4, L5, L6]
variant: default
domain: any
kind: followup
signal_points:
  - escalation judgment
```
"Before you escalated, what had you tried?"


